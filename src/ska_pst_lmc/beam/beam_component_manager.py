# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides an implementation of the BEAM PST component manager."""

from __future__ import annotations

import functools
import json
import logging
import sys
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import (
    AdminMode,
    CommunicationStatus,
    HealthState,
    LoggingLevel,
    ObsState,
    PowerState,
)
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.beam.beam_device_interface import PstBeamDeviceInterface
from ska_pst_lmc.component import as_device_attribute_name
from ska_pst_lmc.component.component_manager import PstComponentManager
from ska_pst_lmc.device_proxy import ChangeEventSubscription, DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.job import DeviceCommandTask, LambdaTask, NoopTask, SequentialTask, Task, TaskExecutor
from ska_pst_lmc.util import TelescopeFacilityEnum
from ska_pst_lmc.util.callback import Callback, callback_safely

TaskResponse = Tuple[TaskStatus, str]
RemoteTaskResponse = Tuple[List[TaskStatus], List[str]]

__all__ = [
    "PstBeamComponentManager",
]

ActionResponse = Tuple[List[str], List[str]]
RemoteDeviceAction = Callable[[PstDeviceProxy], ActionResponse]


class _RemoteJob:
    def __init__(
        self: _RemoteJob,
        job: Task,
        task_executor: TaskExecutor,
        completion_callback: Callback,
        logger: logging.Logger,
    ):
        self._job = job
        self._completion_callback = completion_callback
        self._logger = logger
        self._task_executor = task_executor

    def __call__(
        self: _RemoteJob,
        *args: Any,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs: Any,
    ) -> None:
        def _completion_callback(*arg: Any, **kwargs: Any) -> None:
            self._completion_callback(task_callback)  # type: ignore

        callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)

        try:
            self._task_executor.submit_job(job=self._job, callback=_completion_callback)
        except Exception as e:
            self._logger.warning("Error in submitting long running commands to remote devices", exc_info=True)
            if task_callback:
                task_callback(status=TaskStatus.FAILED, result=str(e), exception=e)


class PstBeamComponentManager(PstComponentManager[PstBeamDeviceInterface]):
    """
    Component manager for the BEAM component in PST.LMC.

    Since the BEAM component is a logical device, this component
    manager is used to orchestrate the process devices, such as
    BEAM, RECV.

    Commands that are executed on this component manager are
    sent to instances of :py:class:`PstDeviceProxy` for each
    device that the BEAM device manages.

    This component manager only takes the fully-qualified device
    name (FQDN) for the remote devices, but uses the
    :py:class:`DeviceProxyFactory` to retrieve instances of the
    device proxies that commands should be sent to.
    """

    _smrb_device: PstDeviceProxy
    _recv_device: PstDeviceProxy
    _dsp_device: PstDeviceProxy
    _stat_device: PstDeviceProxy

    def __init__(
        self: PstBeamComponentManager,
        *,
        device_interface: PstBeamDeviceInterface,
        logger: logging.Logger,
        **kwargs: Any,
    ) -> None:
        """
        Initialise component manager.

        :param smrb_fqdn: the fully qualified device name (FQDN) of the shared memory ring buffer (SMRB) TANGO
            device.
        :param recv_fqdn: the FQDN of the Receive TANGO device.
        :param dsp_fqdn: the FQDN of the Digital Signal processing (DSP) TANGO device.
        :param simulation_mode: enum to track if component should be in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be called when the status of the
            communications channel between the component manager and its component changes
        :param component_fault_callback: callback to be called when the component faults (or stops faulting)
        """
        self._smrb_device = DeviceProxyFactory.get_device(device_interface.smrb_fqdn)
        self._recv_device = DeviceProxyFactory.get_device(device_interface.recv_fqdn)
        self._dsp_device = DeviceProxyFactory.get_device(device_interface.dsp_fqdn)
        self._stat_device = DeviceProxyFactory.get_device(device_interface.stat_fqdn)
        self._remote_devices = [self._smrb_device, self._recv_device, self._dsp_device, self._stat_device]
        self._subscribed = False
        self._pst_task_executor = TaskExecutor(logger=logger)
        self._curr_scan_config: dict | None = None
        self._pst_task_executor.start()

        super().__init__(
            device_interface=device_interface,
            power=PowerState.UNKNOWN,
            fault=None,
            logger=logger,
            **kwargs,
        )

        self._initialise_monitoring_properties()
        self._change_event_subscriptions: List[ChangeEventSubscription] = []

    def __del__(self: PstBeamComponentManager) -> None:
        """Handle shutdown of component manager."""
        self._pst_task_executor.stop()

    def _initialise_monitoring_properties(self: PstBeamComponentManager) -> None:
        """
        Initialise all the monitored properties.

        This method will set all the properties to there default values. This
        calls the `_reset_monitoring_properties` method. Most properties can
        be reset, but the `available_disk_space` property is not reset once
        it has been updated by the system.
        """
        import sys

        self.available_disk_space = sys.maxsize
        self._reset_monitoring_properties()

    def _reset_monitoring_properties(self: PstBeamComponentManager) -> None:
        """
        Reset monitored attributes.

        This method resets the values to a sensible default when not in a configured state.
        """
        from ska_pst_lmc.dsp.dsp_model import DEFAULT_RECORDING_TIME

        # RECV properties
        self.data_received = 0
        self.data_receive_rate = 0.0
        self.data_dropped = 0
        self.data_drop_rate = 0.0
        self.misordered_packets = 0
        self.misordered_packet_rate = 0.0
        self.malformed_packets = 0
        self.malformed_packet_rate = 0.0
        self.misdirected_packets = 0
        self.misdirected_packet_rate = 0.0
        self.checksum_failure_packets = 0
        self.checksum_failure_packet_rate = 0.0
        self.timestamp_sync_error_packets = 0
        self.timestamp_sync_error_packet_rate = 0.0
        self.seq_number_sync_error_packets = 0
        self.seq_number_sync_error_packet_rate = 0.0

        self.data_record_rate = 0.0
        self.data_recorded = 0
        self.available_recording_time = DEFAULT_RECORDING_TIME
        self.ring_buffer_utilisation = 0.0
        self.expected_data_record_rate = 0.0
        self.channel_block_configuration = {}
        self.config_id = ""
        self.scan_id = 0

        # expose disk
        self.disk_capacity = sys.maxsize
        self.disk_used_bytes = 0
        self.disk_used_percentage = 0.0

    @property
    def channel_block_configuration(self: PstBeamComponentManager) -> Dict[str, Any]:
        """Get current channel block configuration."""
        return self._channel_block_configuration

    @channel_block_configuration.setter
    def channel_block_configuration(self: PstBeamComponentManager, config: Dict[str, Any]) -> None:
        """Set channel black configuration."""
        self._channel_block_configuration = config
        self._property_callback("channel_block_configuration", json.dumps(config))

    def _update_channel_block_configuration(
        self: PstBeamComponentManager, subband_beam_configuration: str
    ) -> None:
        """
        Update the channel block configuration.

        This calculates the new channel block configuration and is only called
        after a successful `ConfigureScan` request. It uses the SMRB util to work
        determine the subband configuration and then maps that to what is need
        by the client of the BEAM.MGMT.

        .. code-block:: python

            {
                "num_channel_blocks": 2,
                "channel_blocks": [
                    {
                        "destination_host": "10.10.0.1",
                        "destination_port": 20000,
                        "start_pst_channel": 0,
                        "num_pst_channels": 12,
                    },
                    {
                        "destination_host": "10.10.0.1",
                        "destination_port": 20001,
                        "start_pst_channel": 12,
                        "num_pst_channels": 10,
                    },
                ]
            }
        """
        subband_resources = json.loads(subband_beam_configuration)
        if subband_resources:
            self.channel_block_configuration = {
                "num_channel_blocks": subband_resources["common"]["nsubband"],
                "channel_blocks": [
                    {
                        "destination_host": subband["data_host"],
                        "destination_port": subband["data_port"],
                        "start_pst_channel": subband["start_channel"],
                        "num_pst_channels": subband["end_channel"] - subband["start_channel"],
                    }
                    for subband in subband_resources["subbands"].values()
                ],
            }
        else:
            self.channel_block_configuration = {}

    @property
    def data_receive_rate(self: PstBeamComponentManager) -> float:
        """Get current received data rate in Gb/s."""
        return self._data_receive_rate

    @data_receive_rate.setter
    def data_receive_rate(self: PstBeamComponentManager, data_receive_rate: float) -> None:
        """Set current received data rate in Gb/s."""
        self._data_receive_rate = data_receive_rate
        self._property_callback("data_receive_rate", data_receive_rate)

    @property
    def data_received(self: PstBeamComponentManager) -> int:
        """Get current received data in bytes."""
        return self._data_received

    @data_received.setter
    def data_received(self: PstBeamComponentManager, data_received: int) -> None:
        """Set current received data in bytes."""
        self._data_received = data_received
        self._property_callback("data_received", data_received)

    @property
    def data_drop_rate(self: PstBeamComponentManager) -> float:
        """Get current dropped data rate in bytes per second."""
        return self._data_drop_rate

    @data_drop_rate.setter
    def data_drop_rate(self: PstBeamComponentManager, data_drop_rate: float) -> None:
        """Set current dropped data rate in bytes per second."""
        self._data_drop_rate = data_drop_rate
        self._property_callback("data_drop_rate", data_drop_rate)

    @property
    def data_dropped(self: PstBeamComponentManager) -> int:
        """Get current dropped data in bytes."""
        return self._data_dropped

    @data_dropped.setter
    def data_dropped(self: PstBeamComponentManager, data_dropped: int) -> None:
        """Set current dropped data in bytes."""
        self._data_dropped = data_dropped
        self._property_callback("data_dropped", data_dropped)

    @property
    def misordered_packets(self: PstBeamComponentManager) -> int:
        """Get the total number of packets received out of order in the current scan."""
        return self._misordered_packets

    @misordered_packets.setter
    def misordered_packets(self: PstBeamComponentManager, misordered_packets: int) -> None:
        """Set the total number of packets received out of order in the current scan."""
        self._misordered_packets = misordered_packets
        self._property_callback("misordered_packets", misordered_packets)

    @property
    def misordered_packet_rate(self: PstBeamComponentManager) -> float:
        """Get the current rate of packets received out of order in packets/sec."""
        return self._misordered_packet_rate

    @misordered_packet_rate.setter
    def misordered_packet_rate(self: PstBeamComponentManager, misordered_packet_rate: float) -> None:
        """Set the current rate of packets received out of order in packets/sec."""
        self._misordered_packet_rate = misordered_packet_rate
        self._property_callback("misordered_packet_rate", misordered_packet_rate)

    @property
    def malformed_packets(self: PstBeamComponentManager) -> int:
        """Get the total number of malformed packets in the current scan."""
        return self._malformed_packets

    @malformed_packets.setter
    def malformed_packets(self: PstBeamComponentManager, malformed_packets: int) -> None:
        """Set the total number of malformed packets in the current scan."""
        self._malformed_packets = malformed_packets
        self._property_callback("malformed_packets", malformed_packets)

    @property
    def malformed_packet_rate(self: PstBeamComponentManager) -> float:
        """Get the current rate of malformed packets in packets/sec."""
        return self._malformed_packet_rate

    @malformed_packet_rate.setter
    def malformed_packet_rate(self: PstBeamComponentManager, malformed_packet_rate: float) -> None:
        """Set the current rate of malformed packets in packets/sec."""
        self._malformed_packet_rate = malformed_packet_rate
        self._property_callback("malformed_packet_rate", malformed_packet_rate)

    @property
    def misdirected_packets(self: PstBeamComponentManager) -> int:
        """Get the total number of misdirected packets in the current scan."""
        return self._misdirected_packets

    @misdirected_packets.setter
    def misdirected_packets(self: PstBeamComponentManager, misdirected_packets: int) -> None:
        """Set the total number of misdirected packets in the current scan."""
        self._misdirected_packets = misdirected_packets
        self._property_callback("misdirected_packets", misdirected_packets)

    @property
    def misdirected_packet_rate(self: PstBeamComponentManager) -> float:
        """Get the current rate of misdirected packets in packets/sec."""
        return self._misdirected_packet_rate

    @misdirected_packet_rate.setter
    def misdirected_packet_rate(self: PstBeamComponentManager, misdirected_packet_rate: float) -> None:
        """Set the current rate of misdirected packets in packets/sec."""
        self._misdirected_packet_rate = misdirected_packet_rate
        self._property_callback("misdirected_packet_rate", misdirected_packet_rate)

    @property
    def checksum_failure_packets(self: PstBeamComponentManager) -> int:
        """Get the total number of packets with checksum failures for the current scan."""
        return self._checksum_failure_packets

    @checksum_failure_packets.setter
    def checksum_failure_packets(self: PstBeamComponentManager, checksum_failure_packets: int) -> None:
        """Set the total number of packets with checksum failures for the current scan."""
        self._checksum_failure_packets = checksum_failure_packets
        self._property_callback("checksum_failure_packets", checksum_failure_packets)

    @property
    def checksum_failure_packet_rate(self: PstBeamComponentManager) -> float:
        """Get the current rate of packets with checksum failures in packets/sec."""
        return self._checksum_failure_packet_rate

    @checksum_failure_packet_rate.setter
    def checksum_failure_packet_rate(
        self: PstBeamComponentManager, checksum_failure_packet_rate: float
    ) -> None:
        """Set the current rate of packets with checksum failures in packets/sec."""
        self._checksum_failure_packet_rate = checksum_failure_packet_rate
        self._property_callback("checksum_failure_packet_rate", checksum_failure_packet_rate)

    @property
    def timestamp_sync_error_packets(self: PstBeamComponentManager) -> int:
        """Get the total number of packets with timestamp sync errors for the current scan."""
        return self._timestamp_sync_error_packets

    @timestamp_sync_error_packets.setter
    def timestamp_sync_error_packets(
        self: PstBeamComponentManager, timestamp_sync_error_packets: int
    ) -> None:
        """Set the total number of packets with timestamp sync errors for the current scan."""
        self._timestamp_sync_error_packets = timestamp_sync_error_packets
        self._property_callback("timestamp_sync_error_packets", timestamp_sync_error_packets)

    @property
    def timestamp_sync_error_packet_rate(self: PstBeamComponentManager) -> float:
        """Get the current rate of packets with timestamp sync errors in packets/sec."""
        return self._timestamp_sync_error_packet_rate

    @timestamp_sync_error_packet_rate.setter
    def timestamp_sync_error_packet_rate(
        self: PstBeamComponentManager, timestamp_sync_error_packet_rate: float
    ) -> None:
        """Set the current rate of packets with timestamp sync errors in packets/sec."""
        self._timestamp_sync_error_packet_rate = timestamp_sync_error_packet_rate
        self._property_callback("timestamp_sync_error_packet_rate", timestamp_sync_error_packet_rate)

    @property
    def seq_number_sync_error_packets(self: PstBeamComponentManager) -> int:
        """
        Get the total number of packets with seq.

        number sync error for the current scan.
        """
        return self._seq_number_sync_error_packets

    @seq_number_sync_error_packets.setter
    def seq_number_sync_error_packets(
        self: PstBeamComponentManager, seq_number_sync_error_packets: int
    ) -> None:
        """
        Set the total number of packets with seq.

        number sync error for the current scan.
        """
        self._seq_number_sync_error_packets = seq_number_sync_error_packets
        self._property_callback("seq_number_sync_error_packets", seq_number_sync_error_packets)

    @property
    def seq_number_sync_error_packet_rate(self: PstBeamComponentManager) -> float:
        """
        Get the current rate of packets with seq.

        number sync error in packets/sec.
        """
        return self._seq_number_sync_error_packet_rate

    @seq_number_sync_error_packet_rate.setter
    def seq_number_sync_error_packet_rate(
        self: PstBeamComponentManager, seq_number_sync_error_packet_rate: float
    ) -> None:
        """
        Set the current rate of packets with seq.

        number sync error in packets/sec.
        """
        self._seq_number_sync_error_packet_rate = seq_number_sync_error_packet_rate
        self._property_callback("seq_number_sync_error_packet_rate", seq_number_sync_error_packet_rate)

    @property
    def data_record_rate(self: PstBeamComponentManager) -> float:
        """Get current data write rate in bytes per second."""
        return self._data_record_rate

    @data_record_rate.setter
    def data_record_rate(self: PstBeamComponentManager, data_record_rate: int) -> None:
        """Set current data write rate in bytes per second."""
        self._data_record_rate = data_record_rate
        self._property_callback("data_record_rate", data_record_rate)

    @property
    def data_recorded(self: PstBeamComponentManager) -> int:
        """Get current amount of bytes written to file."""
        return self._data_recorded

    @data_recorded.setter
    def data_recorded(self: PstBeamComponentManager, data_recorded: int) -> None:
        """Set current amount of bytes written to file."""
        self._data_recorded = data_recorded
        self._property_callback("data_recorded", data_recorded)

    @property
    def disk_capacity(self: PstBeamComponentManager) -> int:
        """Get size, in bytes, for the disk used for recording scan data."""
        return self._disk_capacity

    @disk_capacity.setter
    def disk_capacity(self: PstBeamComponentManager, disk_capacity: int) -> None:
        """Set size, in bytes, for the disk used for recording scan data."""
        self._disk_capacity = disk_capacity
        self._property_callback("disk_capacity", disk_capacity)

    @property
    def disk_used_bytes(self: PstBeamComponentManager) -> int:
        """Get the current amount, in bytes, of disk used used."""
        return self._disk_used_bytes

    @disk_used_bytes.setter
    def disk_used_bytes(self: PstBeamComponentManager, disk_used_bytes: int) -> None:
        """Set the current amount, in bytes, of disk used."""
        self._disk_used_bytes = disk_used_bytes
        self._property_callback("disk_used_bytes", disk_used_bytes)

    @property
    def disk_used_percentage(self: PstBeamComponentManager) -> float:
        """Get the percentage of used disk space for recording of scan data."""
        return self._disk_used_percentage

    @disk_used_percentage.setter
    def disk_used_percentage(self: PstBeamComponentManager, disk_used_percentage: float) -> None:
        """Set the percent of used disk space for recording of scan data."""
        self._disk_used_percentage = disk_used_percentage
        self._property_callback("disk_used_percentage", disk_used_percentage)

    @property
    def available_disk_space(self: PstBeamComponentManager) -> int:
        """Get available bytes for disk to be written to during scan."""
        return self._available_disk_space

    @available_disk_space.setter
    def available_disk_space(self: PstBeamComponentManager, available_disk_space: int) -> None:
        """Set available bytes for disk to be written to during scan."""
        self._available_disk_space = available_disk_space
        self._property_callback("available_disk_space", available_disk_space)

    @property
    def available_recording_time(self: PstBeamComponentManager) -> float:
        """Get the available recording time, for the disk being written to during the scan, in seconds."""
        return self._available_recording_time

    @available_recording_time.setter
    def available_recording_time(self: PstBeamComponentManager, available_recording_time: float) -> None:
        """Set the available recording time, for the disk being written to during the scan, in seconds."""
        self._available_recording_time = available_recording_time
        self._property_callback("available_recording_time", available_recording_time)

    @property
    def ring_buffer_utilisation(self: PstBeamComponentManager) -> float:
        """Get current utilisation of ring buffer for current scan configuration."""
        return self._ring_buffer_utilisation

    @ring_buffer_utilisation.setter
    def ring_buffer_utilisation(self: PstBeamComponentManager, ring_buffer_utilisation: float) -> None:
        """Set current utilisation of ring buffer for current scan configuration."""
        self._ring_buffer_utilisation = ring_buffer_utilisation
        self._property_callback("ring_buffer_utilisation", ring_buffer_utilisation)

    @property
    def expected_data_record_rate(self: PstBeamComponentManager) -> float:
        """Get the expected data rate for DSP output for current scan configuration."""
        return self._expected_data_record_rate

    @expected_data_record_rate.setter
    def expected_data_record_rate(self: PstBeamComponentManager, expected_data_record_rate: float) -> None:
        """Set the expected data rate for DSP output for current scan configuration."""
        self._expected_data_record_rate = expected_data_record_rate
        self._property_callback("expected_data_record_rate", expected_data_record_rate)

    def _handle_subdevice_obs_state_event(
        self: PstBeamComponentManager, device: PstDeviceProxy, obs_state: ObsState
    ) -> None:
        """
        Handle a change in the a subdevice's obsState.

        Currently this just handles that a subdevice goes into a FAULT state. However, this could be used for
        knowning when the device has moved out of FAULT or when it has stopped scanning.

        :param device: the device proxy for the subordinate device.
        :type device: PstDeviceProxy
        :param obs_state: the new obsState of a subordinated device.
        :type obs_state: ObsState
        """
        self.logger.debug(f"Recevied an update to {device._fqdn}.obsState. New value is {obs_state}")
        if obs_state == ObsState.FAULT:
            fault_msg: str = device.healthFailureMessage
            self.logger.warning(f"Recevied a FAULT for {device.fqdn}. Fault msg = '{fault_msg}'")
            self._device_interface.handle_subdevice_fault(device_fqdn=device.fqdn, fault_msg=fault_msg)

    def _simulation_mode_changed(self: PstBeamComponentManager) -> None:
        """
        Set simulation mode state.

        :param simulation_mode: the new simulation mode value.
        :type simulation_mode: :py:class:`SimulationMode`
        """
        # ensure we set the subordinate devices into to the same simulation mode.
        self._smrb_device.simulationMode = self.simulation_mode
        self._recv_device.simulationMode = self.simulation_mode
        self._dsp_device.simulationMode = self.simulation_mode
        self._stat_device.simulationMode = self.simulation_mode

    def _handle_communication_state_change(
        self: PstBeamComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            # fake going through states to have the communication established.
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._push_component_state_update(fault=None, power=PowerState.OFF)
            self._device_interface.update_health_state(health_state=HealthState.OK)
        elif communication_state == CommunicationStatus.DISABLED:
            self._push_component_state_update(fault=None, power=PowerState.UNKNOWN)
            self._update_communication_state(CommunicationStatus.DISABLED)
            self._device_interface.update_health_state(health_state=HealthState.UNKNOWN)

    def update_admin_mode(self: PstBeamComponentManager, admin_mode: AdminMode) -> None:
        """
        Update the admin mode of the remote devices.

        The adminMode of the remote devices should only be managed through the BEAM
        device, and this method is called from the :py:class:`PstBeam` device to
        make sure that the component manager will update the remote devices.
        """
        self._smrb_device.adminMode = admin_mode
        self._recv_device.adminMode = admin_mode
        self._dsp_device.adminMode = admin_mode
        self._stat_device.adminMode = admin_mode

    def _submit_remote_job(
        self: PstBeamComponentManager,
        job: Task,
        task_callback: Callback,
        completion_callback: Callback,
    ) -> TaskResponse:
        remote_job = _RemoteJob(
            job,
            task_executor=self._pst_task_executor,
            completion_callback=completion_callback,
            logger=self.logger,
        )

        return self.submit_task(
            remote_job,
            task_callback=task_callback,
        )

    def _subscribe_change_events(self: PstBeamComponentManager) -> None:
        """Subscribe to monitoring attributes of remote devices."""
        self.logger.debug(f"{self.device_name} subscribing to monitoring events")
        subscriptions_config = {
            self._recv_device: [
                "data_receive_rate",
                "data_received",
                "data_dropped",
                "data_drop_rate",
                "misordered_packets",
                "misordered_packet_rate",
                "malformed_packets",
                "malformed_packet_rate",
                "misdirected_packets",
                "misdirected_packet_rate",
                "checksum_failure_packets",
                "checksum_failure_packet_rate",
                "timestamp_sync_error_packets",
                "timestamp_sync_error_packet_rate",
                "seq_number_sync_error_packets",
                "seq_number_sync_error_packet_rate",
                "subband_beam_configuration",
                "obs_state",
            ],
            self._dsp_device: [
                "data_record_rate",
                "data_recorded",
                "available_disk_space",
                "available_recording_time",
                "disk_capacity",
                "disk_used_bytes",
                "disk_used_percentage",
                "obs_state",
            ],
            self._smrb_device: [
                "ring_buffer_utilisation",
                "obs_state",
            ],
            self._stat_device: [
                "obs_state",
            ],
        }

        def _set_attr(attribute: str, value: Any) -> None:
            try:
                setattr(self, attribute, value)
            except Exception:
                self.logger.exception(f"Error in trying to set value to attribute {attribute}", exc_info=True)

        def _subscribe_change_event(device: PstDeviceProxy, attribute: str) -> ChangeEventSubscription:
            try:
                device_attribute = as_device_attribute_name(attribute)

                if attribute == "subband_beam_configuration":
                    callback = self._update_channel_block_configuration
                elif attribute == "obs_state":
                    callback = functools.partial(self._handle_subdevice_obs_state_event, device)
                else:
                    callback = functools.partial(_set_attr, attribute)

                return device.subscribe_change_event(
                    attribute_name=device_attribute,
                    callback=callback,
                )
            except Exception:
                self.logger.exception(f"Error in subscribing to change event of {device}")
                raise

        self._change_event_subscriptions = [
            _subscribe_change_event(device, property)
            for device, property_names in subscriptions_config.items()
            for property in property_names
        ]

    def _unsubscribe_change_events(self: PstBeamComponentManager) -> None:
        """Unsubscribe from current monitoring attributes of remote devices."""
        for s in self._change_event_subscriptions:
            s.unsubscribe()

        self._change_event_subscriptions = []

    @check_communicating
    def on(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            try:
                self.logger.debug("All the 'On' commands have completed.")
                self._subscribe_change_events()
                self._push_component_state_update(power=PowerState.ON)
                task_callback(status=TaskStatus.COMPLETED, result="Completed")
            except Exception as e:
                self.logger.exception("Error occured when dealing with turning on BEAM", exc_info=True)
                task_callback(status=TaskStatus.FAILED, exception=e)

        return self._submit_remote_job(
            job=DeviceCommandTask(
                devices=self._remote_devices,
                action=lambda d: d.On(),
                command_name="On",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def off(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of the command changes
        """
        from tango import DevState

        def _completion_callback(task_callback: Callable) -> None:
            try:
                self.logger.debug("All the 'Off' commands have completed.")
                self._push_component_state_update(power=PowerState.OFF)
                task_callback(status=TaskStatus.COMPLETED, result="Completed")
            except Exception as e:
                self.logger.exception("Error occured when dealing with turning off BEAM", exc_info=True)
                task_callback(status=TaskStatus.FAILED, exception=e)

        # need to unsubscribe from monitoring events.
        self._unsubscribe_change_events()

        devices = [d for d in self._remote_devices if d.state() != DevState.OFF]

        return self._submit_remote_job(
            job=DeviceCommandTask(
                devices=devices,
                action=lambda d: d.Off(),
                command_name="Off",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def standby(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Put the component is standby.

        :param task_callback: callback to be called when the status of the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Standby' commands have completed.")
            self._push_component_state_update(power=PowerState.STANDBY)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandTask(
                devices=self._remote_devices,
                action=lambda d: d.Standby(),
                command_name="Standby",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def reset(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Reset the component.

        :param task_callback: callback to be called when the status of the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Reset' commands have completed.")
            self._push_component_state_update(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandTask(
                devices=self._remote_devices,
                action=lambda d: d.Reset(),
                command_name="Reset",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def _as_pst_configure_scan_request(self: PstBeamComponentManager, configuration: Dict[str, Any]) -> dict:
        """Convert configure scan request into a PST request string."""
        common_configure = configuration["common"]
        pst_configuration = configuration["pst"]["scan"]

        if self._device_interface.facility == TelescopeFacilityEnum.Low:
            # force using a low Frequency Band if the facility is SKALow
            common_configure["frequency_band"] = "low"

        return {
            **common_configure,
            **pst_configuration,
        }

    def validate_configure_scan(
        self: PstBeamComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Validate the configure scan request."""
        if "eb_id" not in configuration["common"]:
            return (TaskStatus.FAILED, "expected 'eb_id' to be set in common section of request.")

        request_str = json.dumps(self._as_pst_configure_scan_request(configuration))

        validation_task = DeviceCommandTask(
            devices=[self._dsp_device, self._recv_device, self._smrb_device, self._stat_device],
            action=lambda d: d.ValidateConfigureScan(request_str),
            command_name="ValidateConfigureScan",
        )

        try:
            self._pst_task_executor.submit_job(job=validation_task)
            return (TaskStatus.COMPLETED, "Completed")
        except Exception as e:
            self.logger.warning(f"Error in validating against core apps: {str(e)}", exc_info=True)
            return (TaskStatus.FAILED, str(e))

    def configure_scan(
        self: PstBeamComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure scan for the component.

        :param configuration: the scan configuration.
        :type configuration: Dict[str, Any]
        """
        # we only care about PST and common parts of the JSON
        # when sending to subordinated devices. Merge these into on configuration
        # request
        pst_configuration = self._as_pst_configure_scan_request(configuration=configuration)
        request_str = json.dumps(pst_configuration)

        def _completion_callback(task_callback: Callable) -> None:
            from ska_pst_lmc.dsp.dsp_util import generate_dsp_scan_request

            self.logger.debug("All the 'ConfigureScan' commands have completed.")
            self._push_component_state_update(configured=True)

            # Update monitored properties
            self.config_id = configuration["common"]["config_id"]
            self._curr_scan_config = configuration
            dsp_scan_request = generate_dsp_scan_request(pst_configuration)
            self.expected_data_record_rate = dsp_scan_request["bytes_per_second"]

            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    # first do configre_beam on SMRB
                    DeviceCommandTask(
                        devices=[self._smrb_device],
                        action=lambda d: d.ConfigureBeam(request_str),
                        command_name="ConfigureBeam",
                    ),
                    # now do configure_beam on DSP, RECV, and STAT, as this can be done in parallel
                    DeviceCommandTask(
                        devices=[self._dsp_device, self._recv_device, self._stat_device],
                        action=lambda d: d.ConfigureBeam(request_str),
                        command_name="ConfigureBeam",
                    ),
                    # now configure scan on SMRB, RECV, and STAT (smrb is no-op) in parallel
                    DeviceCommandTask(
                        devices=[self._smrb_device, self._recv_device, self._stat_device],
                        action=lambda d: d.ConfigureScan(request_str),
                        command_name="ConfigureScan",
                    ),
                    # now configure scan on the DSP device.
                    DeviceCommandTask(
                        devices=[self._dsp_device],
                        action=lambda d: d.ConfigureScan(request_str),
                        command_name="ConfigureScan",
                    ),
                ]
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def deconfigure_scan(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure scan for this component."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'DeconfigureScan' commands have completed.")
            self._curr_scan_config = None
            self._push_component_state_update(configured=False)
            self._reset_monitoring_properties()
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    # need to deconfigure scan of all processes, this can be done in parallel.
                    DeviceCommandTask(
                        devices=self._remote_devices,
                        action=lambda d: d.DeconfigureScan(),
                        command_name="DeconfigureScan",
                    ),
                    # need to release the ring buffer clients before deconfiguring SMRB
                    DeviceCommandTask(
                        devices=[self._dsp_device, self._recv_device, self._stat_device],
                        action=lambda d: d.DeconfigureBeam(),
                        command_name="DeconfigureBeam",
                    ),
                    DeviceCommandTask(
                        devices=[self._smrb_device],
                        action=lambda d: d.DeconfigureBeam(),
                        command_name="DeconfigureBeam",
                    ),
                ],
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def start_scan(
        self: PstBeamComponentManager, args: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Start scanning."""
        scan_id = str(args["scan_id"])

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Scan' commands have completed.")
            self._push_component_state_update(scanning=True)
            self.scan_id = int(scan_id)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    LambdaTask(
                        action=lambda: self._write_scan_config_to_output_dir(scan_id),
                        name="write_scan_config_to_output_dir",
                    ),
                    DeviceCommandTask(
                        devices=self._remote_devices,
                        action=lambda d: d.Scan(scan_id),
                        command_name="Scan",
                    ),
                ]
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def _write_scan_config_to_output_dir(self: PstBeamComponentManager, scan_id: str) -> None:
        """Write the scan configuration out as JSON."""
        import pathlib

        self.logger.debug(f"Writing scan configuration for scan {scan_id}")

        # dump current scan configuration as JSON
        params = {
            "eb_id": self._curr_scan_config["common"]["eb_id"],  # type: ignore
            "subsystem_id": self._device_interface.subsystem_id,
            "scan_id": scan_id,
        }

        output_dir_str = self._device_interface.scan_output_dir_pattern
        for k, v in params.items():
            output_dir_str = output_dir_str.replace(f"<{k}>", v)

        try:
            output_dir = pathlib.Path(output_dir_str)
            output_dir.mkdir(parents=True, exist_ok=True)

            scan_configuration_path = output_dir / "scan_configuration.json"

            self.logger.info(f"Writing scan configuration for scan {scan_id} to {scan_configuration_path}")

            with open(scan_configuration_path, "w") as f:
                json.dump(self._curr_scan_config, f)

        except Exception:
            self.logger.exception("Error in writting output file.", exc_info=True)
            raise

    def stop_scan(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'EndScan' commands have completed.")
            self._push_component_state_update(scanning=False)
            self.scan_id = 0
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        # need to stop_scan on RECV before DSP and STAT, then SMRB
        return self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    DeviceCommandTask(
                        devices=[self._recv_device],
                        action=lambda d: d.EndScan(),
                        command_name="EndScan",
                    ),
                    DeviceCommandTask(
                        devices=[self._dsp_device, self._stat_device],
                        action=lambda d: d.EndScan(),
                        command_name="EndScan",
                    ),
                    DeviceCommandTask(
                        devices=[self._smrb_device],
                        action=lambda d: d.EndScan(),
                        command_name="EndScan",
                    ),
                ]
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def _abort_task(self: PstBeamComponentManager, remote_devices: List[PstDeviceProxy]) -> Task:
        # find devices that need to be put into an aborted state. These are any that
        # are not in ABORTED, FAULT or EMPTY
        devices_to_abort = [
            d for d in remote_devices if d.obsState not in [ObsState.ABORTED, ObsState.FAULT, ObsState.EMPTY]
        ]

        abort_subtask: Task = NoopTask()
        if len(devices_to_abort) > 0:
            abort_subtask = DeviceCommandTask(
                devices=devices_to_abort,
                action=lambda d: d.Abort(),
                command_name="Abort",
            )
        return abort_subtask

    def abort(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""
        # return self.abort_commands(task_callback=task_callback)

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Abort' commands have completed.")
            self._push_component_state_update(scanning=False)
            self.abort_commands()
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    LambdaTask(
                        action=lambda: callback_safely(task_callback, status=TaskStatus.IN_PROGRESS),
                        name="abort_in_progress",
                    ),
                    self._abort_task([self._recv_device]),
                    self._abort_task([self._dsp_device, self._stat_device]),
                    self._abort_task([self._smrb_device]),
                ]
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

        return TaskStatus.IN_PROGRESS, "Aborting"

    def obsreset(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Reset the component and put it into a READY state."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'ObsReset' commands have completed.")
            self._push_component_state_update(configured=False)
            self._device_interface.update_health_state(health_state=HealthState.OK)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        abort_recv_subtask: Task = self._abort_task([self._recv_device])
        abort_readers_subtask: Task = self._abort_task([self._dsp_device, self._stat_device])
        abort_smrb_subtask: Task = self._abort_task([self._smrb_device])

        # call ObsReset on devices that aren't in EMPTY state.  This will move them
        # into IDLE state.
        #
        # Cannot reset devices in parallel.  This will reset the devices in the following order:
        # DSP, RECV, and then SMRB
        devices_to_reset = [d for d in reversed(self._remote_devices) if d.obsState != ObsState.EMPTY]
        obsreset_subtasks: List[Task] = []
        if len(devices_to_reset) > 0:
            obsreset_subtasks = [
                DeviceCommandTask(
                    devices=[d],
                    action=lambda d: d.ObsReset(),
                    command_name="ObsReset",
                )
                for d in devices_to_reset
            ]

        return self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    abort_recv_subtask,
                    abort_readers_subtask,
                    abort_smrb_subtask,
                    *obsreset_subtasks,
                ],
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def go_to_fault(
        self: PstBeamComponentManager, fault_msg: str, task_callback: Callback = None
    ) -> TaskResponse:
        """Put all the sub-devices into a FAULT state."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'GoToFault' commands have completed.")
            self._push_component_state_update(obsfault=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
            self._device_interface.handle_fault(fault_msg=fault_msg)

        return self._submit_remote_job(
            job=SequentialTask(
                subtasks=[
                    DeviceCommandTask(
                        devices=[self._recv_device],
                        action=lambda d: d.GoToFault(fault_msg),
                        command_name="GoToFault",
                    ),
                    DeviceCommandTask(
                        devices=[self._dsp_device, self._stat_device],
                        action=lambda d: d.GoToFault(fault_msg),
                        command_name="GoToFault",
                    ),
                    DeviceCommandTask(
                        devices=[self._smrb_device],
                        action=lambda d: d.GoToFault(fault_msg),
                        command_name="GoToFault",
                    ),
                ]
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def set_logging_level(self: PstBeamComponentManager, log_level: LoggingLevel) -> None:
        """
        Set LoggingLevel of all the sub-devices.

        :param log_level: The required TANGO LoggingLevel
        :returns: None.
        """
        for remote_device in self._remote_devices:
            remote_device.loggingLevel = log_level

    def set_monitoring_polling_rate(self: PstBeamComponentManager, monitor_polling_rate: int) -> None:
        """Set the monitoring polling rate on the subordinate devices."""
        for d in self._remote_devices:
            d.monitoringPollingRate = monitor_polling_rate
