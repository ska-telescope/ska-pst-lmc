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
from threading import Event
from typing import Any, Callable, Dict, List, Optional, Tuple

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import AdminMode, CommunicationStatus, PowerState
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import as_device_attribute_name
from ska_pst_lmc.component.component_manager import PstComponentManager
from ska_pst_lmc.device_proxy import ChangeEventSubscription, DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.util import DeviceCommandJob, Job, SequentialJob, submit_job
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
        job: Job,
        completion_callback: Callback,
        logger: logging.Logger,
    ):
        self._job = job
        self._completion_callback = completion_callback
        self._logger = logger

    def __call__(
        self: _RemoteJob,
        *args: Any,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs: Any,
    ) -> None:
        def _completion_callback() -> None:
            self._completion_callback(task_callback)  # type: ignore

        callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)

        try:
            submit_job(job=self._job, callback=_completion_callback)
        except Exception as e:
            self._logger.warning("Error in submitting long running commands to remote devices", exc_info=True)
            if task_callback:
                task_callback(status=TaskStatus.FAILED, result=str(e), exception=e)


class PstBeamComponentManager(PstComponentManager):
    """Component manager for the BEAM component in PST.LMC.

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

    def __init__(
        self: PstBeamComponentManager,
        device_name: str,
        smrb_fqdn: str,
        recv_fqdn: str,
        dsp_fqdn: str,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        *args: Any,
        property_callback: Callable[[str, Any], None],
        **kwargs: Any,
    ) -> None:
        """Initialise component manager.

        :param smrb_fqdn: the fully qualified device name (FQDN) of the
            shared memory ring buffer (SMRB) TANGO device.
        :param recv_fqdn: the FQDN of the Receive TANGO device.
        :param dsp_fqdn: the FQDN of the Digital Signal processing (DSP) TANGO device.
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        self._smrb_device = DeviceProxyFactory.get_device(smrb_fqdn)
        self._recv_device = DeviceProxyFactory.get_device(recv_fqdn)
        self._dsp_device = DeviceProxyFactory.get_device(dsp_fqdn)
        self._remote_devices = [self._smrb_device, self._recv_device, self._dsp_device]
        self._subscribed = False
        self._property_callback = property_callback

        super().__init__(
            device_name,
            logger,
            communication_state_callback,
            component_state_callback,
            *args,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

        self._initialise_monitoring_properties()
        self._change_event_subscriptions: List[ChangeEventSubscription] = []

    def _initialise_monitoring_properties(self: PstBeamComponentManager) -> None:
        """
        Initialise all the monitored properties.

        This method will set all the properties to there default values. This
        calls the `_reset_monitoring_properties` method. Most properties can
        be reset, but the `disk_available_bytes` property is not reset once
        it has been updated by the system.
        """
        import sys

        self.disk_available_bytes = sys.maxsize
        self._reset_monitoring_properties()

    def _reset_monitoring_properties(self: PstBeamComponentManager) -> None:
        """
        Reset monitored attributes.

        This method resets the values to a sensible default when not in
        a configured state.
        """
        from ska_pst_lmc.dsp.dsp_model import DEFAULT_RECORDING_TIME

        self.data_receive_rate = 0.0
        self.data_received = 0
        self.data_dropped = 0
        self.data_drop_rate = 0.0
        self.data_record_rate = 0.0
        self.bytes_written = 0
        self.available_recording_time = DEFAULT_RECORDING_TIME
        self.ring_buffer_utilisation = 0.0
        self.expected_data_rate = 0.0
        self.channel_block_configuration = {}
        self.config_id = ""
        self.scan_id = 0

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
        """Update the channel block configuration.

        This calculates the new channel block configuration and is only called
        after a successful `ConfigureScan` request. It uses the SMRB util to work
        determine the subband configuration and then maps that to what is need
        by the client of the BEAM.MGMT.

        .. code-block:: python

            {
                "num_channel_blocks": 2,
                "channel_blocks": [
                    {
                        "data_host": "10.10.0.1",
                        "data_port": 20000,
                        "start_channel": 0,
                        "num_channels": 12,
                    },
                    {
                        "data_host": "10.10.0.1",
                        "data_port": 20001,
                        "start_channel": 12,
                        "num_channels": 10,
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
                        "data_host": subband["data_host"],
                        "data_port": subband["data_port"],
                        "start_channel": subband["start_channel"],
                        "num_channels": subband["end_channel"] - subband["start_channel"],
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
    def data_record_rate(self: PstBeamComponentManager) -> float:
        """Get current data write rate in bytes per second."""
        return self._data_record_rate

    @data_record_rate.setter
    def data_record_rate(self: PstBeamComponentManager, data_record_rate: int) -> None:
        """Set current data write rate in bytes per second."""
        self._data_record_rate = data_record_rate
        self._property_callback("data_record_rate", data_record_rate)

    @property
    def bytes_written(self: PstBeamComponentManager) -> int:
        """Get current amount of bytes written to file."""
        return self._bytes_written

    @bytes_written.setter
    def bytes_written(self: PstBeamComponentManager, bytes_written: int) -> None:
        """Set current amount of bytes written to file."""
        self._bytes_written = bytes_written
        self._property_callback("bytes_written", bytes_written)

    @property
    def disk_available_bytes(self: PstBeamComponentManager) -> int:
        """Get available bytes for disk to be written to during scan."""
        return self._disk_available_bytes

    @disk_available_bytes.setter
    def disk_available_bytes(self: PstBeamComponentManager, disk_available_bytes: int) -> None:
        """Set available bytes for disk to be written to during scan."""
        self._disk_available_bytes = disk_available_bytes
        self._property_callback("disk_available_bytes", disk_available_bytes)

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
    def expected_data_rate(self: PstBeamComponentManager) -> float:
        """Get the expected data rate for DSP output for current scan configuration."""
        return self._expected_data_rate

    @expected_data_rate.setter
    def expected_data_rate(self: PstBeamComponentManager, expected_data_rate: float) -> None:
        """Set the expected data rate for DSP output for current scan configuration."""
        self._expected_data_rate = expected_data_rate
        self._property_callback("expected_data_rate", expected_data_rate)

    def _simulation_mode_changed(self: PstBeamComponentManager) -> None:
        """Set simulation mode state.

        :param simulation_mode: the new simulation mode value.
        :type simulation_mode: :py:class:`SimulationMode`
        """
        # ensure we set the subordinate devices into to the same simulation mode.
        self._smrb_device.simulationMode = self.simulation_mode
        self._recv_device.simulationMode = self.simulation_mode
        self._dsp_device.simulationMode = self.simulation_mode

    def _handle_communication_state_change(
        self: PstBeamComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            # fake going through states to have the communication established.
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._push_component_state_update(fault=None, power=PowerState.OFF)
        elif communication_state == CommunicationStatus.DISABLED:
            self._push_component_state_update(fault=None, power=PowerState.UNKNOWN)
            self._update_communication_state(CommunicationStatus.DISABLED)

    def update_admin_mode(self: PstBeamComponentManager, admin_mode: AdminMode) -> None:
        """Update the admin mode of the remote devices.

        The adminMode of the remote devices should only be managed through the BEAM
        device, and this method is called from the :py:class:`PstBeam` device to
        make sure that the component manager will update the remote devices.
        """
        self._smrb_device.adminMode = admin_mode
        self._recv_device.adminMode = admin_mode
        self._dsp_device.adminMode = admin_mode

    def _submit_remote_job(
        self: PstBeamComponentManager,
        job: Job,
        task_callback: Callback,
        completion_callback: Callback,
    ) -> TaskResponse:
        remote_job = _RemoteJob(job, completion_callback=completion_callback, logger=self.logger)

        return self.submit_task(
            remote_job,
            task_callback=task_callback,
        )

    def _subscribe_change_events(self: PstBeamComponentManager) -> None:
        """Subscribe to monitoring attributes of remote devices."""
        self.logger.debug(f"{self._device_name} subscribing to monitoring events")
        subscriptions_config = {
            self._recv_device: [
                "data_receive_rate",
                "data_received",
                "data_dropped",
                "data_drop_rate",
                "subband_beam_configuration",
            ],
            self._dsp_device: [
                "data_record_rate",
                "bytes_written",
                "disk_available_bytes",
                "available_recording_time",
            ],
            self._smrb_device: ["ring_buffer_utilisation"],
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

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'On' commands have completed.")
            self._push_component_state_update(power=PowerState.ON)

            self._subscribe_change_events()

            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
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

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Off' commands have completed.")
            self._push_component_state_update(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        # need to unsubscribe from monitoring events.
        self._unsubscribe_change_events()

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
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

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Standby' commands have completed.")
            self._push_component_state_update(power=PowerState.STANDBY)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
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

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Reset' commands have completed.")
            self._push_component_state_update(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.Reset(),
                command_name="Reset",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

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
        common_configure = configuration["common"]
        pst_configuration = configuration["pst"]["scan"]

        def _completion_callback(task_callback: Callable) -> None:
            from ska_pst_lmc.dsp.dsp_util import generate_dsp_scan_request

            self.logger.debug("All the 'ConfigureScan' commands have completed.")
            self._push_component_state_update(configured=True)

            # Update monitored properties
            self.config_id = configuration["common"]["config_id"]
            dsp_scan_request = generate_dsp_scan_request(pst_configuration)
            self.expected_data_rate = dsp_scan_request["bytes_per_second"]

            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        request = {
            **common_configure,
            **pst_configuration,
        }
        request_str = json.dumps(request)

        return self._submit_remote_job(
            job=SequentialJob(
                tasks=[
                    # first do configre_beam on SMRB
                    DeviceCommandJob(
                        devices=[self._smrb_device],
                        action=lambda d: d.ConfigureBeam(request_str),
                        command_name="ConfigureBeam",
                    ),
                    # now do configure_beam on DSP and RECV, this can be done in parallel
                    DeviceCommandJob(
                        devices=[self._dsp_device, self._recv_device],
                        action=lambda d: d.ConfigureBeam(request_str),
                        command_name="ConfigureBeam",
                    ),
                    # now configure scan on SMRB and RECV (smrb is no-op) in parallel
                    DeviceCommandJob(
                        devices=[self._smrb_device, self._recv_device],
                        action=lambda d: d.ConfigureScan(request_str),
                        command_name="ConfigureScan",
                    ),
                    # now configure scan on the DSP device.
                    DeviceCommandJob(
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
            self._push_component_state_update(configured=False)
            self._reset_monitoring_properties()
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=SequentialJob(
                tasks=[
                    # need to deconfigure scan of all processes, this can be done in parallel.
                    DeviceCommandJob(
                        devices=self._remote_devices,
                        action=lambda d: d.DeconfigureScan(),
                        command_name="DeconfigureScan",
                    ),
                    # need to release the ring buffer clients before deconfiguring SMRB
                    DeviceCommandJob(
                        devices=[self._dsp_device, self._recv_device],
                        action=lambda d: d.DeconfigureBeam(),
                        command_name="DeconfigureBeam",
                    ),
                    DeviceCommandJob(
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
        scan_id = args["scan_id"]

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Scan' commands have completed.")
            self._push_component_state_update(scanning=True)
            self.scan_id = scan_id
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.Scan(str(scan_id)),
                command_name="Scan",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def stop_scan(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'EndScan' commands have completed.")
            self._push_component_state_update(scanning=False)
            self.scan_id = 0
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.EndScan(),
                command_name="EndScan",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def abort(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""
        # raise NotImplementedError("SubarrayComponentManager is abstract.")
        self._smrb_device.Abort()
        self._recv_device.Abort()
        self._dsp_device.Abort()
        return self.abort_commands(task_callback)

    def obsreset(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Reset the component and put it into a READY state."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'ObsReset' commands have completed.")
            self._push_component_state_update(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=SequentialJob(
                tasks=[
                    # This will put the subordinate classes into IDLE state
                    DeviceCommandJob(
                        devices=self._remote_devices,
                        action=lambda d: d.ObsReset(),
                        command_name="ObsReset",
                    ),
                    # need to release the ring buffer clients before deconfiguring SMRB
                    DeviceCommandJob(
                        devices=[self._dsp_device, self._recv_device],
                        action=lambda d: d.DeconfigureBeam(),
                        command_name="DeconfigureBeam",
                    ),
                    DeviceCommandJob(
                        devices=[self._smrb_device],
                        action=lambda d: d.DeconfigureBeam(),
                        command_name="DeconfigureBeam",
                    ),
                ],
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def go_to_fault(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Put all the sub-devices into a FAULT state."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'GoToFault' commands have completed.")
            self._push_component_state_update(obsfault=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.GoToFault(),
                command_name="GoToFault",
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )
