# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the DSP PST component manager."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import MonitorDataHandler, PstApiComponentManager, TaskResponse
from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorData, DspDiskMonitorDataStore
from ska_pst_lmc.dsp.dsp_process_api import PstDspProcessApi, PstDspProcessApiGrpc, PstDspProcessApiSimulator
from ska_pst_lmc.dsp.dsp_util import calculate_dsp_subband_resources
from ska_pst_lmc.util.callback import Callback, callback_safely, wrap_callback

__all__ = ["PstDspComponentManager"]


class PstDspComponentManager(PstApiComponentManager):
    """Component manager for the DSP component for the PST.LMC subsystem."""

    _api: PstDspProcessApi

    def __init__(
        self: PstDspComponentManager,
        device_name: str,
        process_api_endpoint: str,
        logger: logging.Logger,
        monitor_data_callback: Callable[[DspDiskMonitorData], None],
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[..., None],
        api: Optional[PstDspProcessApi] = None,
        monitor_polling_rate: int = 5000,
        *args: Any,
        property_callback: Callable[[str, Any], None],
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
        self._monitor_data_store = DspDiskMonitorDataStore()
        self._monitor_data_handler = MonitorDataHandler(
            data_store=self._monitor_data_store,
            monitor_data_callback=monitor_data_callback,
        )
        self._monitor_polling_rate = monitor_polling_rate
        self._property_callback = property_callback

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

    def _update_api(self: PstDspComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstDspProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )
        else:
            self._api = PstDspProcessApiGrpc(
                client_id=self._device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )

    @property
    def _monitor_data(self: PstDspComponentManager) -> DspDiskMonitorData:
        """Get current monitoring data."""
        return self._monitor_data_handler.monitor_data

    @property
    def disk_capacity(self: PstDspComponentManager) -> int:
        """Get size, in bytes, for the disk for DSP processing for this beam."""
        return self._monitor_data.disk_capacity

    @property
    def available_disk_space(self: PstDspComponentManager) -> int:
        """Get currently available bytes of the disk."""
        return self._monitor_data.available_disk_space

    @property
    def disk_used_bytes(self: PstDspComponentManager) -> int:
        """Get amount of bytes used on the disk that DSP is writing to."""
        return self._monitor_data.disk_used_bytes

    @property
    def disk_used_percentage(self: PstDspComponentManager) -> float:
        """Get the percentage of used disk space that DSP is writing to."""
        return self._monitor_data.disk_used_percentage

    @property
    def data_recorded(self: PstDspComponentManager) -> int:
        """Get total amount of bytes written in current scan across all subbands."""
        return self._monitor_data.data_recorded

    @property
    def data_record_rate(self: PstDspComponentManager) -> float:
        """Get total rate of writing to disk across all subbands, in bytes/second."""
        return self._monitor_data.data_record_rate

    @property
    def available_recording_time(self: PstDspComponentManager) -> float:
        """Get estimated available recording time left for current scan."""
        return self._monitor_data.available_recording_time

    @property
    def subband_data_recorded(self: PstDspComponentManager) -> List[int]:
        """Get a list of bytes written, one record per subband."""
        return self._monitor_data.subband_data_recorded

    @property
    def subband_data_record_rate(self: PstDspComponentManager) -> List[float]:
        """Get a list of current rate of writing per subband, in bytes/seconds."""
        return self._monitor_data.subband_data_record_rate

    def _get_disk_stats_from_api(self: PstDspComponentManager) -> None:
        """Update the disk usage details calling API.

        This gets the `disk_capacity` and `available_disk_space` from the API via
        calling the :py:meth:`ProcessApi.get_env` method.

        This is used to get the value of the disk capacity and the  available disk
        space before the DSP.DISK starts monitoring. This is needed as BEAM.MGMT
        needs to know the value before we monitor.
        """
        environment_values = self._api.get_env()
        self._monitor_data_store.update_disk_stats(**environment_values)
        self._monitor_data_handler.update_monitor_data(notify=False)

        for k, v in environment_values.items():
            self._property_callback(k, v)

    @check_communicating
    def on(self: PstDspComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Callback = None,
            task_abort_event: Optional[threading.Event] = None,
            **kwargs: Any,
        ) -> None:
            callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)
            self._push_component_state_update(power=PowerState.ON)

            # need to submit this as a background task, so clients of On know
            # that we're in the right state so they can subscribe to events
            # and get correct values.
            self.submit_task(self._get_disk_stats_from_api)

            callback_safely(task_callback, status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    def configure_beam(
        self: PstDspComponentManager, resources: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure the beam of the the component with the resources.

        :param resources: resources to be assigned
        """
        dsp_resources = calculate_dsp_subband_resources(self.beam_id, request_params=resources)

        # deal only with subband 1 for now.
        self.logger.debug(f"Submitting API with dsp_resources={dsp_resources[1]}")

        def _task(task_callback: Callback = None) -> None:
            self._api.configure_beam(resources=dsp_resources[1], task_callback=wrap_callback(task_callback))
            self._get_disk_stats_from_api()
            # callback_safely(task_callback)

        return self._submit_background_task(_task, task_callback=task_callback)

    def start_scan(
        self: PstDspComponentManager, args: Dict[str, Any], task_callback: Callback = None
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

    def stop_scan(self: PstDspComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning."""

        def _task(task_callback: Callback = None) -> None:
            self._api.stop_scan(task_callback=wrap_callback(task_callback))

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
