# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the SMRB PST component manager."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode

from ska_pst_lmc.component.component_manager import PstApiComponentManager
from ska_pst_lmc.smrb.smrb_process_api import (
    PstSmrbProcessApi,
    PstSmrbProcessApiGrpc,
    PstSmrbProcessApiSimulator,
)

__all__ = ["PstSmrbComponentManager"]


class PstSmrbComponentManager(PstApiComponentManager):
    """Component manager for the SMRB component for the PST.LMC subsystem."""

    _api: PstSmrbProcessApi

    def __init__(
        self: PstSmrbComponentManager,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool, PowerState], None],
        api: Optional[PstSmrbProcessApi] = None,
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
        """
        api = api or PstSmrbProcessApiSimulator(
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
        self: PstSmrbComponentManager, communication_state: CommunicationStatus
    ) -> None:
        """Handle change in communication state."""
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            self._connect_to_smrb()
        elif communication_state == CommunicationStatus.DISABLED:
            self._disconnect_from_smrb()

    def _connect_to_smrb(self: PstSmrbComponentManager) -> None:
        """Establish connection to SMRB component."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._api.connect()
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._component_state_callback(fault=None, power=PowerState.OFF)

    def _disconnect_from_smrb(self: PstSmrbComponentManager) -> None:
        """Establish connection to SMRB component."""
        self._api.disconnect()
        self._update_communication_state(CommunicationStatus.DISABLED)
        self._component_state_callback(fault=None, power=PowerState.UNKNOWN)

    @property
    def ring_buffer_utilisation(self: PstSmrbComponentManager) -> float:
        """Get the percentage of the ring buffer elements that are full of data.

        :returns: the percentage of the ring buffer elements that are full of data.
        :rtype: float
        """
        return self._api.monitor_data.ring_buffer_utilisation

    @property
    def ring_buffer_size(self: PstSmrbComponentManager) -> int:
        """Get the capacity of the ring buffer, in bytes.

        :returns: the capacity of the ring buffer, in bytes.
        :rtype: int
        """
        return self._api.monitor_data.ring_buffer_size

    @property
    def number_subbands(self: PstSmrbComponentManager) -> int:
        """Get the number of sub-bands.

        :returns: the number of sub-bands.
        :rtype: int
        """
        return self._api.monitor_data.number_subbands

    @property
    def subband_ring_buffer_utilisations(self: PstSmrbComponentManager) -> List[float]:
        """Get the percentage of full ring buffer elements for each sub-band.

        :returns: the percentage of full ring buffer elements for each sub-band.
        :rtype: List[float]
        """
        return self._api.monitor_data.subband_ring_buffer_utilisations

    @property
    def subband_ring_buffer_sizes(self: PstSmrbComponentManager) -> List[int]:
        """Get the capacity of ring buffers for each sub-band.

        :returns: the capacity of ring buffers, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self._api.monitor_data.subband_ring_buffer_sizes

    def _simulation_mode_changed(self: PstSmrbComponentManager) -> None:
        """Handle change of simulation mode."""
        curr_communication_state = self.communication_state
        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.stop_communicating()

        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstSmrbProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )
        else:
            self._api = PstSmrbProcessApiGrpc(
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )

        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.start_communicating()
