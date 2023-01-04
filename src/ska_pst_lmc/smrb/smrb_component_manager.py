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
from typing import Any, Dict, List, Optional

from ska_tango_base.control_model import PowerState, SimulationMode

from ska_pst_lmc.component import (
    MonitorDataHandler,
    PstApiComponentManager,
    PstApiDeviceInterface,
    TaskResponse,
)
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData, SmrbMonitorDataStore
from ska_pst_lmc.smrb.smrb_process_api import (
    PstSmrbProcessApi,
    PstSmrbProcessApiGrpc,
    PstSmrbProcessApiSimulator,
)
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources
from ska_pst_lmc.util.callback import Callback, wrap_callback

__all__ = ["PstSmrbComponentManager"]


class PstSmrbComponentManager(PstApiComponentManager[SmrbMonitorData, PstSmrbProcessApi]):
    """Component manager for the SMRB component for the PST.LMC subsystem."""

    def __init__(
        self: PstSmrbComponentManager,
        *,
        device_interface: PstApiDeviceInterface[SmrbMonitorData],
        logger: logging.Logger,
        api: Optional[PstSmrbProcessApi] = None,
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
            f"Setting up SMRB component manager with device_name='{device_interface.device_name}'"
            + f"and api_endpoint='{device_interface.process_api_endpoint}'"
        )
        api = api or PstSmrbProcessApiSimulator(
            logger=logger,
            component_state_callback=device_interface.handle_component_state_change,
        )

        # Set up handling of monitor data.
        self._monitor_data_handler = MonitorDataHandler(
            data_store=SmrbMonitorDataStore(),
            monitor_data_callback=device_interface.handle_monitor_data_update,
        )

        super().__init__(
            device_interface=device_interface,
            api=api,
            logger=logger,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

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

    @property
    def _monitor_data(self: PstSmrbComponentManager) -> SmrbMonitorData:
        """Get monitor data from data handler."""
        return self._monitor_data_handler.monitor_data

    def _update_api(self: PstSmrbComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstSmrbProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )
        else:
            self._api = PstSmrbProcessApiGrpc(
                client_id=self.device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )

    def configure_beam(
        self: PstSmrbComponentManager, resources: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure beam resources in the component.

        :param resources: resources to be assigned
        """
        smrb_resources = calculate_smrb_subband_resources(self.beam_id, request_params=resources)

        # deal only with subband 1 for now.
        self.logger.debug(f"Submitting API with smrb_resources={smrb_resources[1]}")

        return self._submit_background_task(
            functools.partial(self._api.configure_beam, resources=smrb_resources[1]),
            task_callback=task_callback,
        )

    def start_scan(
        self: PstSmrbComponentManager, args: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Start scanning."""

        def _task(task_callback: Callback = None) -> None:
            self._api.start_scan(args=args, task_callback=wrap_callback(task_callback))
            self._api.monitor(
                # for now only handling 1 subband
                subband_monitor_data_callback=self._monitor_data_handler.handle_subband_data,
                polling_rate=self._monitor_polling_rate,
            )

        return self._submit_background_task(_task, task_callback=task_callback)

    def stop_scan(self: PstSmrbComponentManager, task_callback: Callback = None) -> TaskResponse:
        """End scanning."""

        def _task(task_callback: Callback = None) -> None:
            self._api.stop_scan(task_callback=wrap_callback(task_callback))

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
