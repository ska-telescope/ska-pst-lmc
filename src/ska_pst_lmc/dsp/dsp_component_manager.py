# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the DSP PST component manager."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, List, Optional

from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode

from ska_pst_lmc.component import MonitorDataHandler, PstApiComponentManager, TaskResponse
from ska_pst_lmc.dsp.dsp_model import DspMonitorData, DspMonitorDataStore
from ska_pst_lmc.dsp.dsp_process_api import PstDspProcessApi, PstDspProcessApiGrpc, PstDspProcessApiSimulator
from ska_pst_lmc.dsp.dsp_util import calculate_dsp_subband_resources

__all__ = ["PstDspComponentManager"]


class PstDspComponentManager(PstApiComponentManager):
    """Component manager for the DSP component for the PST.LMC subsystem."""

    _api: PstDspProcessApi

    def __init__(
        self: PstDspComponentManager,
        device_name: str,
        process_api_endpoint: str,
        logger: logging.Logger,
        monitor_data_callback: Callable[[DspMonitorData], None],
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[..., None],
        api: Optional[PstDspProcessApi] = None,
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
            f"Setting up DSP component manager with device_name='{device_name}'"
            + "and api_endpoint='{process_api_endpoint}'"
        )
        self.api_endpoint = process_api_endpoint
        api = api or PstDspProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )

        # need a lock for updating component data
        self._monitor_data_handler = MonitorDataHandler(
            data_store=DspMonitorDataStore(),
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

    @property
    def beam_id(self: PstDspComponentManager) -> int:
        """Return the beam id for the current DSP component.

        This should be determined from the FQDN as that should have
        the beam 1 encoded in it.
        """
        return 1

    def _update_api(self: PstDspComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstDspProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )
        else:
            self._api = PstDspProcessApiGrpc(
                client_id=self._device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._component_state_callback,
            )

    @property
    def _monitor_data(self: PstDspComponentManager) -> DspMonitorData:
        """Get current monitoring data."""
        return self._monitor_data_handler.monitor_data

    @property
    def disk_capacity(self: PstDspComponentManager) -> int:
        """Get size, in bytes, for the disk for DSP processing for this beam."""
        return self._monitor_data.disk_capacity

    @property
    def disk_available_bytes(self: PstDspComponentManager) -> int:
        """Get currently available bytes of the disk."""
        return self._monitor_data.disk_available_bytes

    @property
    def disk_used_bytes(self: PstDspComponentManager) -> int:
        """Get amount of bytes used on the disk that DSP is writing to."""
        return self._monitor_data.disk_used_bytes

    @property
    def disk_used_percentage(self: PstDspComponentManager) -> float:
        """Get the percentage of used disk space that DSP is writing to."""
        return self._monitor_data.disk_used_percentage

    @property
    def bytes_written(self: PstDspComponentManager) -> int:
        """Get total amount of bytes written in current scan across all subbands."""
        return self._monitor_data.bytes_written

    @property
    def write_rate(self: PstDspComponentManager) -> float:
        """Get total rate of writing to disk across all subbands, in bytes/second."""
        return self._monitor_data.write_rate

    @property
    def available_recording_time(self: PstDspComponentManager) -> float:
        """Get estimated available recording time left for current scan."""
        return self._monitor_data.available_recording_time

    @property
    def subband_bytes_written(self: PstDspComponentManager) -> List[int]:
        """Get a list of bytes written, one record per subband."""
        return self._monitor_data.subband_bytes_written

    @property
    def subband_write_rate(self: PstDspComponentManager) -> List[float]:
        """Get a list of current rate of writing per subband, in bytes/seconds."""
        return self._monitor_data.subband_write_rate

    def assign(self: PstDspComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """
        dsp_resources = calculate_dsp_subband_resources(self.beam_id, request_params=resources)

        # deal only with subband 1 for now.
        self.logger.debug(f"Submitting API with dsp_resources={dsp_resources[1]}")

        return self._submit_background_task(
            functools.partial(self._api.configure_beam, resources=dsp_resources[1]),
            task_callback=task_callback,
        )

    def scan(self: PstDspComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""

        def _task(task_callback: Callable[..., None]) -> None:
            self._api.start_scan(args, task_callback=task_callback)
            self._api.monitor(
                # for now only handling 1 subband
                subband_monitor_data_callback=self._monitor_data_handler.handle_subband_data,
                polling_rate=self._monitor_polling_rate,
            )

        return self._submit_background_task(_task, task_callback=task_callback)

    def end_scan(self: PstDspComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""

        def _task(task_callback: Callable[..., None]) -> None:
            self._api.stop_scan(task_callback=task_callback)

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
