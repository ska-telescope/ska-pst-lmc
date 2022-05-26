# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the RECV PST component manager."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from ska_tango_base.control_model import CommunicationStatus, PowerState

from ska_pst_lmc.component import PstApiComponentManager
from ska_pst_lmc.receive.receive_process_api import PstReceiveProcessApi, PstReceiveProcessApiSimulator


class PstReceiveComponentManager(PstApiComponentManager):
    """Component manager for the RECV component for the PST.LMC subsystem."""

    _api: PstReceiveProcessApi

    def __init__(
        self: PstReceiveComponentManager,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        api: Optional[PstReceiveProcessApi] = None,
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
        :param api: optional API instance, used to override during testing.
        """
        api = api or PstReceiveProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )

        super().__init__(
            api,
            logger,
            communication_state_callback,
            component_state_callback,
            *args,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

    def _handle_communication_state_change(
        self: PstReceiveComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            self._connect_to_receive()
        elif communication_state == CommunicationStatus.DISABLED:
            self._disconnect_from_receive()

    def _connect_to_receive(self: PstReceiveComponentManager) -> None:
        """Establish connection to RECV component."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._api.connect()
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._component_state_callback(fault=None, power=PowerState.OFF)

    def _disconnect_from_receive(self: PstReceiveComponentManager) -> None:
        self._api.disconnect()
        self._update_communication_state(CommunicationStatus.DISABLED)
        self._component_state_callback(fault=None, power=PowerState.UNKNOWN)

    @property
    def received_rate(self: PstReceiveComponentManager) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self._api.monitor_data.received_rate

    @property
    def received_data(self: PstReceiveComponentManager) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self._api.monitor_data.received_data

    @property
    def dropped_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return self._api.monitor_data.dropped_rate

    @property
    def dropped_data(self: PstReceiveComponentManager) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return self._api.monitor_data.dropped_data

    @property
    def misordered_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self._api.monitor_data.misordered_packets

    @property
    def malformed_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of malformed packets received during the current scan.

        :returns: total number of malformed packets received during the current scan.
        :rtype: int
        """
        return self._api.monitor_data.malformed_packets

    @property
    def relative_weight(self: PstReceiveComponentManager) -> float:
        """Get the time averages of all relative weights for the current scan.

        :returns: time average of all relative weights for the current scan.
        :rtype: float
        """
        return self._api.monitor_data.relative_weight

    @property
    def relative_weights(self: PstReceiveComponentManager) -> List[float]:
        """Get the time average of relative weights for each channel in the current scan.

        :returns: time average of relative weights for each channel in the current scan.
        :rtype: list(float)
        """
        return self._api.monitor_data.relative_weights
