# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the RECV PST component manager."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode

from ska_pst_lmc.component import PstApiComponentManager
from ska_pst_lmc.component.component_manager import TaskResponse
from ska_pst_lmc.component.monitor_data_handler import MonitorDataHandler
from ska_pst_lmc.receive.receive_model import ReceiveData, ReceiveDataStore
from ska_pst_lmc.receive.receive_process_api import (
    PstReceiveProcessApi,
    PstReceiveProcessApiGrpc,
    PstReceiveProcessApiSimulator,
)
from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources


class PstReceiveComponentManager(PstApiComponentManager):
    """Component manager for the RECV component for the PST.LMC subsystem."""

    _api: PstReceiveProcessApi

    def __init__(
        self: PstReceiveComponentManager,
        device_name: str,
        process_api_endpoint: str,
        logger: logging.Logger,
        monitor_data_callback: Callable[[ReceiveData], None],
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[..., None],
        network_interface: str,
        udp_port: int,
        api: Optional[PstReceiveProcessApi] = None,
        monitor_polling_rate: int = 5000,
        *args: Any,
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
            f"Setting up RECV component manager with device_name='{device_name}'"
            + "and api_endpoint='{process_api_endpoint}'"
        )
        self.api_endpoint = process_api_endpoint
        api = api or PstReceiveProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
        self._network_interface = network_interface
        self._udp_port = udp_port

        # Set up handling of monitor data.
        self._monitor_data_handler = MonitorDataHandler(
            data_store=ReceiveDataStore(),
            monitor_data_callback=monitor_data_callback,
        )
        self._monitor_polling_rate = monitor_polling_rate

        super().__init__(
            device_name,
            api,
            logger,
            communication_state_callback,
            component_state_callback,
            *args,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

    def _update_api(self: PstReceiveComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstReceiveProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )
        else:
            self._api = PstReceiveProcessApiGrpc(
                client_id=self._device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )

    @property
    def beam_id(self: PstReceiveComponentManager) -> int:
        """Return the beam id for the current RECV component.

        This should be determined from the FQDN as that should have
        the beam 1 encoded in it.
        """
        return 1

    @property
    def received_rate(self: PstReceiveComponentManager) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self._monitor_data.received_rate

    @property
    def received_data(self: PstReceiveComponentManager) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self._monitor_data.received_data

    @property
    def dropped_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return self._monitor_data.dropped_rate

    @property
    def dropped_data(self: PstReceiveComponentManager) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return self._monitor_data.dropped_data

    @property
    def misordered_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self._monitor_data.misordered_packets

    @property
    def _monitor_data(self: PstReceiveComponentManager) -> ReceiveData:
        """Get monitor data from data handler."""
        return self._monitor_data_handler.monitor_data

    def assign(self: PstReceiveComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """
        recv_resources = calculate_receive_subband_resources(
            self.beam_id,
            request_params=resources,
            data_host=self._network_interface,
            data_port=self._udp_port,
        )
        self.logger.debug(f"Submitting API with recv_resources={recv_resources}")

        # deal only with subband 1 for now. otherwise we have to deal with tracking
        # multiple long running tasks.
        def _task(task_callback: Callable) -> None:
            common_resources = recv_resources["common"]
            subband_resources = recv_resources["subbands"][1]

            resources = {
                "common": common_resources,
                "subband": subband_resources,
            }

            self._api.configure_beam(resources=resources, task_callback=task_callback)

        return self._submit_background_task(
            _task,
            task_callback=task_callback,
        )

    def start_scan(self: PstReceiveComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""

        def _task(task_callback: Callable[..., None]) -> None:
            self._api.start_scan(args, task_callback=task_callback)
            self._api.monitor(
                # for now only handling 1 subband
                subband_monitor_data_callback=self._monitor_data_handler.handle_subband_data,
                polling_rate=self._monitor_polling_rate,
            )

        return self._submit_background_task(_task, task_callback=task_callback)

    def stop_scan(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""

        def _task(task_callback: Callable[..., None]) -> None:
            self._api.stop_scan(task_callback=task_callback)

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
