# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the SMRB PST component manager."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, List, Optional

from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode

from ska_pst_lmc.component.component_manager import PstApiComponentManager, TaskResponse
from ska_pst_lmc.smrb.smrb_process_api import (
    PstSmrbProcessApi,
    PstSmrbProcessApiGrpc,
    PstSmrbProcessApiSimulator,
)
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources

__all__ = ["PstSmrbComponentManager"]


class PstSmrbComponentManager(PstApiComponentManager):
    """Component manager for the SMRB component for the PST.LMC subsystem."""

    _api: PstSmrbProcessApi

    def __init__(
        self: PstSmrbComponentManager,
        device_name: str,
        process_api_endpoint: str,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool, PowerState], None],
        api: Optional[PstSmrbProcessApi] = None,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This
            is used within the gRPC process to identify who is
            doing the calling.
        :param process_api_endpoint: the endpoint of the gRPC process.
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        logger.debug(
            f"Setting up SMRB component manager with device_name='{device_name}'"
            + "and api_endpoint='{process_api_endpoint}'"
        )
        self.api_endpoint = process_api_endpoint
        api = api or PstSmrbProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
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

        def _task() -> None:
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self._api.connect()
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._component_state_callback(fault=None, power=PowerState.OFF)

        self._background_task_processor.submit_task(_task)

    def _disconnect_from_smrb(self: PstSmrbComponentManager) -> None:
        """Establish connection to SMRB component."""
        self._api.disconnect()
        self._update_communication_state(CommunicationStatus.DISABLED)
        self._component_state_callback(fault=None, power=PowerState.UNKNOWN)

    @property
    def beam_id(self: PstSmrbComponentManager) -> int:
        """Return the beam id for the current SMRB component.

        This should be determined from the FQDN as that should have
        the beam 1 encoded in it.
        """
        return 1

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
                client_id=self._device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )

        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.start_communicating()

    def assign(self: PstSmrbComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """
        smrb_resources = calculate_smrb_subband_resources(self.beam_id, request_params=resources)

        # deal only with subband 1 for now.
        self.logger.debug(f"Submitting API with smrb_resources={smrb_resources[1]}")

        return self._submit_background_task(
            functools.partial(self._api.assign_resources, resources=smrb_resources[1]),
            task_callback=task_callback,
        )
