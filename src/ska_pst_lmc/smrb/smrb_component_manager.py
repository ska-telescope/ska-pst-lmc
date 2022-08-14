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
import threading
from typing import Any, Callable, List, Optional

from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode

from ska_pst_lmc.component.component_manager import PstApiComponentManager, TaskResponse
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData, SmrbMonitorDataStore, SubbandMonitorData
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
        monitor_data_callback: Callable[[SmrbMonitorData], None],
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool, PowerState], None],
        api: Optional[PstSmrbProcessApi] = None,
        monitor_polling_rate: int = 5000,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This
            is used within the gRPC process to identify who is
            doing the calling.
        :param process_api_endpoint: the endpoint of the gRPC process.
        :param logger: a logger for this object is to use.
        :param monitor_data_callback: the callback that monitoring data
            should call when data has been received. This should be
            used by the Tango device to be notified when data has been
            updated.
        :param communication_state_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes.
        :param component_state_callback: callback to be called when the
            component state changes.
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

        # need a lock for updating component data
        self._monitor_lock = threading.Lock()
        self._monitor_data_store = SmrbMonitorDataStore()
        self._monitor_data = SmrbMonitorData()
        self._monitor_data_callback = monitor_data_callback
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
        return self._monitor_data.ring_buffer_utilisation

    @property
    def ring_buffer_size(self: PstSmrbComponentManager) -> int:
        """Get the capacity of the ring buffer, in bytes.

        :returns: the capacity of the ring buffer, in bytes.
        :rtype: int
        """
        return self._monitor_data.ring_buffer_size

    @property
    def number_subbands(self: PstSmrbComponentManager) -> int:
        """Get the number of sub-bands.

        :returns: the number of sub-bands.
        :rtype: int
        """
        return self._monitor_data.number_subbands

    @property
    def ring_buffer_read(self: PstSmrbComponentManager) -> int:
        """Get the amount of data, in bytes, that has been read.

        :returns: the amount of data that has been read.
        :rtype: int
        """
        return self._monitor_data.ring_buffer_read

    @property
    def ring_buffer_written(self: PstSmrbComponentManager) -> int:
        """Get the amount of data, in bytes, that has been written.

        :returns: the amount of data that has been written.
        :rtype: int
        """
        return self._monitor_data.ring_buffer_written

    @property
    def subband_ring_buffer_utilisations(self: PstSmrbComponentManager) -> List[float]:
        """Get the percentage of full ring buffer elements for each sub-band.

        :returns: the percentage of full ring buffer elements for each sub-band.
        :rtype: List[float]
        """
        return self._monitor_data.subband_ring_buffer_utilisations

    @property
    def subband_ring_buffer_sizes(self: PstSmrbComponentManager) -> List[int]:
        """Get the capacity of ring buffers for each sub-band.

        :returns: the capacity of ring buffers, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self._monitor_data.subband_ring_buffer_sizes

    @property
    def subband_ring_buffer_read(self: PstSmrbComponentManager) -> List[int]:
        """Get the capacity of ring buffers for each sub-band.

        :returns: the capacity of ring buffers, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self._monitor_data.subband_ring_buffer_read

    @property
    def subband_ring_buffer_written(self: PstSmrbComponentManager) -> List[int]:
        """Get the capacity of ring buffers for each sub-band.

        :returns: the capacity of ring buffers, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self._monitor_data.subband_ring_buffer_written

    def _update_api(self: PstSmrbComponentManager) -> None:
        """Update instance of API based on simulation mode."""
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

    def scan(self: PstSmrbComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""

        def _task(task_callback: Callable[..., None]) -> None:
            self._api.scan(args, task_callback=task_callback)
            self._api.monitor(
                # for now only handling 1 subband
                subband_monitor_data_callback=self._handle_subband_monitor_data,
                polling_rate=self._monitor_polling_rate,
            )

        return self._submit_background_task(_task, task_callback=task_callback)

    def end_scan(self: PstSmrbComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""

        def _task(task_callback: Callable[..., None]) -> None:
            self._api.end_scan(task_callback=task_callback)

            # reset the monitoring data
            self._monitor_data = SmrbMonitorData()
            self._monitor_data_callback(self._monitor_data)

        return self._submit_background_task(_task, task_callback=task_callback)

    def obsreset(self: PstSmrbComponentManager, task_callback: Callable) -> TaskResponse:
        """Handle observation reset.

        This occurs when the device is in ABORTED or FAULT state. This is used to make
        sure that the device is put back in to an IDLE state.
        """
        return self._submit_background_task(
            functools.partial(self._api.reset),
            task_callback=task_callback,
        )

    def restart(self: PstSmrbComponentManager, task_callback: Callable) -> TaskResponse:
        """Handle device restart command.

        This occurs when the device is in ABORTED or FAULT state but the operator wants
        to also release all the resources of device. Calling this will ensure that the
        device is deconfigured and resources are deallocated.
        """
        return self._submit_background_task(
            functools.partial(self._api.restart),
            task_callback=task_callback,
        )

    def _handle_subband_monitor_data(
        self: PstSmrbComponentManager,
        *args: Any,
        subband_id: int,
        subband_data: SubbandMonitorData,
        **kwargs: dict,
    ) -> None:
        """Handle receiving of a sub-band monitor data update."""
        self.logger.info(f"Received subband data for subband {subband_id}. Data=\n{subband_data}")
        with self._monitor_lock:
            self._monitor_data_store.subband_data[subband_id] = subband_data
            self._monitor_data = self._monitor_data_store.get_smrb_monitor_data()
            self._monitor_data_callback(self._monitor_data)
