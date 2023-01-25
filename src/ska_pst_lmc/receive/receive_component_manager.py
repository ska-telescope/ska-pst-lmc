# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the RECV PST component manager."""

from __future__ import annotations

import logging
from functools import cache
from typing import Any, Dict, List, Optional

from ska_tango_base.control_model import PowerState, SimulationMode

from ska_pst_lmc.component import PstApiComponentManager, PstApiDeviceInterface
from ska_pst_lmc.component.component_manager import TaskResponse
from ska_pst_lmc.component.monitor_data_handler import MonitorDataHandler
from ska_pst_lmc.receive.receive_model import ReceiveData, ReceiveDataStore
from ska_pst_lmc.receive.receive_process_api import (
    PstReceiveProcessApi,
    PstReceiveProcessApiGrpc,
    PstReceiveProcessApiSimulator,
)
from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources
from ska_pst_lmc.util.callback import Callback, wrap_callback


class PstReceiveComponentManager(PstApiComponentManager[ReceiveData, PstReceiveProcessApi]):
    """Component manager for the RECV component for the PST.LMC subsystem."""

    def __init__(
        self: PstReceiveComponentManager,
        *,
        device_interface: PstApiDeviceInterface[ReceiveData],
        logger: logging.Logger,
        api: Optional[PstReceiveProcessApi] = None,
        **kwargs: Any,
    ):
        """Initialise instance of the component manager.

        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        :param network_interface: the network interface for the RECV subband
            to listen to.
        :param udp_port: the UDP port for RECV subband to listen to.
        :param api: optional API instance, used to override during testing.
        """
        logger.debug(
            f"Setting up RECV component manager with device_name='{device_interface.device_name}'"
            + f"and api_endpoint='{device_interface.process_api_endpoint}'"
        )
        api = api or PstReceiveProcessApiSimulator(
            logger=logger,
            component_state_callback=device_interface.handle_component_state_change,
        )
        self._subband_udp_ports: List[int] = []

        # Set up handling of monitor data.
        self._monitor_data_handler = MonitorDataHandler(
            data_store=ReceiveDataStore(),
            monitor_data_callback=device_interface.handle_monitor_data_update,
        )
        self._data_host: Optional[str] = None

        super().__init__(
            device_interface=device_interface,
            api=api,
            logger=logger,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

        self._subband_beam_configuration: Dict[str, Any] = {}

    def _update_api(self: PstReceiveComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstReceiveProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )
        else:
            self._api = PstReceiveProcessApiGrpc(
                client_id=self.device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )

    @property
    def data_receive_rate(self: PstReceiveComponentManager) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self._monitor_data.data_receive_rate

    @property
    def data_received(self: PstReceiveComponentManager) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self._monitor_data.data_received

    @property
    def data_drop_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return self._monitor_data.data_drop_rate

    @property
    def data_dropped(self: PstReceiveComponentManager) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return self._monitor_data.data_dropped

    @property
    def misordered_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self._monitor_data.misordered_packets

    @property
    def misordered_packet_rate(self: PstReceiveComponentManager) -> float:
        """Get the rate of packets that are received out of order in packets/sec.

        :returns: the rate of packets that are received out of order.
        :rtype: float
        """
        return self._monitor_data.misordered_packet_rate

    @property
    def malformed_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets marked as malformed for the current scan.

        Malformed packets are valid UDP packets, but where contents of
        the UDP payload does not conform to the specification in the
        CBF/PST ICD. Examples of malformation include: bad magic-word
        field, invalid meta-data, incorrect packet size.

        :return: total number of packets marked as malformed for the current scan.
        :rtype: int
        """
        return self._monitor_data.malformed_packets

    @property
    def malformed_packet_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of malformed packets in packets/sec.

        :return: the current rate of malformed packets in packets/seconds.
        :rtype: float
        """
        return self._monitor_data.malformed_packet_rate

    @property
    def misdirected_packets(self: PstReceiveComponentManager) -> int:
        """Get the total of misdirected packets received during current scan.

        Total number of (valid) UDP packets that were unexpectedly received.
        Misdirection could be due to wrong ScanID, Beam ID, Network Interface
        or UDP port. Receiving misdirected packets is a sign that there is
        something wrong with the upstream configuration for the scan.

        :return: the total of misdirected packets received during current scan.
        :rtype: int
        """
        return self._monitor_data.misdirected_packets

    @property
    def misdirected_packet_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of misdirected packets in packets/sec.

        :return: the current rate of misdirected packets in packets/seconds.
        :rtype: float
        """
        return self._monitor_data.misdirected_packet_rate

    @property
    def checksum_failure_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets with a checksum failure in current scan.

        Total number of packets with a UDP, IP header or CRC checksum failure.

        :return: the total number of packets with a checksum failure in current scan.
        :rtype: int
        """
        return self._monitor_data.checksum_failure_packets

    @property
    def checksum_failure_packet_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of packets with a checksum failure in packets/sec.

        :return: the current rate of packets with a checksum failure in packets/seconds.
        :rtype: float
        """
        return self._monitor_data.checksum_failure_packet_rate

    @property
    def timestamp_sync_error_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets with a timestamp sync error for current scan.

        The number of packets received where the timestamp has become
        desynchronised with the packet sequence number * sampling interval

        :return: the total number of packets with a timestamp sync error for current scan.
        :rtype: int
        """
        return self._monitor_data.timestamp_sync_error_packets

    @property
    def timestamp_sync_error_packet_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of packets marked as having a timestamp sync error in packets/sec.

        :return: the current rate of packets marked as having a timestamp sync error
            in packets/seconds.
        :rtype: float
        """
        return self._monitor_data.timestamp_sync_error_packet_rate

    @property
    def seq_number_sync_error_packets(self: PstReceiveComponentManager) -> int:
        """Get total number of packets with a sequence number sync error for current scan.

        The number of packets received where the packet sequence number has
        become desynchronised with the data rate and elapsed time.

        :return: total number of packets with a sequence number sync error for current scan.
        :rtype: int
        """
        return self._monitor_data.seq_number_sync_error_packets

    @property
    def seq_number_sync_error_packet_rate(self: PstReceiveComponentManager) -> float:
        """Get current rate of packets marked as having a sequence number sync error in packets/sec.

        :return: current rate of packets marked as having a sequence number sync error
            in packets/seconds.
        :rtype: float
        """
        return self._monitor_data.seq_number_sync_error_packet_rate

    @property
    def _monitor_data(self: PstReceiveComponentManager) -> ReceiveData:
        """Get monitor data from data handler."""
        return self._monitor_data_handler.monitor_data

    @cache
    def _get_env(self: PstReceiveComponentManager) -> Dict[str, Any]:
        return self._api.get_env()

    @property
    def data_host(self: PstReceiveComponentManager) -> str:
        """Get data host used for receiving data during a scan.

        :return: the data host used for receiving data during a scan.
        :rtype: str
        """
        if self._data_host is None:
            self._data_host = self._get_env()["data_host"]

        return self._data_host

    @property
    def subband_udp_ports(self: PstReceiveComponentManager) -> List[int]:
        """Get data ports used by all the subbands for receiving data during a scan.

        :return: the data host used for receiving data during a scan.
        :rtype: str
        """
        if not self._subband_udp_ports:
            self._subband_udp_ports = [self._get_env()["data_port"]]

        return self._subband_udp_ports

    @property
    def subband_beam_configuration(self: PstReceiveComponentManager) -> Dict[str, Any]:
        """Get the current subband beam configuration.

        This is the current subband beam configuration that is calculated during the
        `configure_beam`.

        :return: the current subband beam configuration.
        :rtype: Dict[str, Any]
        """
        return self._subband_beam_configuration

    @subband_beam_configuration.setter
    def subband_beam_configuration(self: PstReceiveComponentManager, config: Dict[str, Any]) -> None:
        import json

        self._subband_beam_configuration = config
        self._property_callback("subbandBeamConfiguration", json.dumps(self._subband_beam_configuration))

    def configure_beam(
        self: PstReceiveComponentManager, resources: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure beam resources in the component.

        :param resources: resources to be assigned
        """
        # deal only with subband 1 for now. otherwise we have to deal with tracking
        # multiple long running tasks.
        def _task(task_callback: Callback) -> None:
            try:
                recv_resources = calculate_receive_subband_resources(
                    self.beam_id,
                    request_params=resources,
                    data_host=self.data_host,
                    subband_udp_ports=self.subband_udp_ports,
                )
                self.logger.debug(f"Submitting API with recv_resources={recv_resources}")

                subband_resources = {
                    "common": recv_resources["common"],
                    "subband": recv_resources["subbands"][1],
                }

                self._api.configure_beam(
                    resources=subband_resources, task_callback=wrap_callback(task_callback)
                )
                self.subband_beam_configuration = recv_resources
            except Exception:
                self.logger.exception("Error in configuring scan for RECV", exc_info=True)
                raise

        return self._submit_background_task(
            _task,
            task_callback=task_callback,
        )

    def deconfigure_beam(self: PstReceiveComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure the RECV component's beam configuration.

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """

        def _task(task_callback: Callback) -> None:
            self._api.deconfigure_beam(task_callback=wrap_callback(task_callback))
            self.subband_beam_configuration = {}

        return self._submit_background_task(_task, task_callback=task_callback)

    def start_scan(
        self: PstReceiveComponentManager, args: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Start scanning."""

        def _task(task_callback: Callback) -> None:
            try:
                self._api.start_scan(args=args, task_callback=wrap_callback(task_callback))
                self._api.monitor(
                    # for now only handling 1 subband
                    subband_monitor_data_callback=self._monitor_data_handler.handle_subband_data,
                    polling_rate=self._monitor_polling_rate,
                )
            except Exception:
                self.logger.exception("Error in starting scan for RECV.MGMT", exc_info=True)
                raise

        return self._submit_background_task(_task, task_callback=task_callback)

    def stop_scan(self: PstReceiveComponentManager, task_callback: Callback = None) -> TaskResponse:
        """End scanning."""

        def _task(task_callback: Callback) -> None:
            self._api.stop_scan(task_callback=wrap_callback(task_callback))

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
