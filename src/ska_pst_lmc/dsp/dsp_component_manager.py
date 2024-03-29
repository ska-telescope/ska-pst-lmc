# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides an implementation of the DSP PST component manager."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from ska_tango_base.control_model import PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import (
    MonitorDataHandler,
    PstApiComponentManager,
    PstApiDeviceInterface,
    TaskResponse,
)
from ska_pst_lmc.dsp.disk_monitor_task import DiskMonitorTask
from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorData, DspDiskMonitorDataStore
from ska_pst_lmc.dsp.dsp_process_api import PstDspProcessApi, PstDspProcessApiGrpc, PstDspProcessApiSimulator
from ska_pst_lmc.dsp.dsp_util import calculate_dsp_subband_resources
from ska_pst_lmc.util.callback import Callback, wrap_callback

__all__ = ["PstDspComponentManager"]


class PstDspComponentManager(PstApiComponentManager[DspDiskMonitorData, PstDspProcessApi]):
    """Component manager for the DSP component for the PST.LMC subsystem."""

    _api: PstDspProcessApi

    def __init__(
        self: PstDspComponentManager,
        *,
        device_interface: PstApiDeviceInterface[DspDiskMonitorData],
        logger: logging.Logger,
        api: Optional[PstDspProcessApi] = None,
        **kwargs: Any,
    ):
        """
        Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This is used within the gRPC process to identify
            who is doing the calling.
        :param process_api_endpoint: the endpoint of the gRPC process.
        :param logger: a logger for this object is to use.
        :param monitor_data_callback: the callback that monitoring data should call when data has been
            received. This should be used by the TANGO device to be notified when data has been updated.
        :param communication_state_callback: callback to be called when the status of the communications
            channel between the component manager and its component changes.
        :param component_state_callback: callback to be called when the component state changes.
        """
        logger.debug(
            f"Setting up DSP component manager with device_name='{device_interface.device_name}'"
            + f"and api_endpoint='{device_interface.process_api_endpoint}'"
        )
        api = api or PstDspProcessApiSimulator(
            logger=logger,
            component_state_callback=device_interface.handle_component_state_change,
        )

        # need a lock for updating component data
        self._monitor_data_store = DspDiskMonitorDataStore()
        self._monitor_data_handler = MonitorDataHandler(
            data_store=self._monitor_data_store,
            monitor_data_callback=device_interface.handle_monitor_data_update,
        )

        self._disk_monitor_task: DiskMonitorTask | None = None

        super().__init__(
            device_interface=device_interface,
            api=api,
            logger=logger,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

    def stop_disk_stats_monitoring(self: PstDspComponentManager) -> None:
        """Stop monitoring of disk usage."""
        if self._disk_monitor_task is not None:
            self._disk_monitor_task.shutdown()
            self._disk_monitor_task = None

    def _update_api(self: PstDspComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstDspProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )
        else:
            self._api = PstDspProcessApiGrpc(
                client_id=self.device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )

    def _create_disk_monitor_task(self: PstDspComponentManager) -> None:
        """Create a instance of a DiskMonitorTask."""
        self._disk_monitor_task = DiskMonitorTask(
            stats_action=self._get_disk_stats_from_api,
            logger=self.logger,
            monitoring_polling_rate=self.monitoring_polling_rate,
        )

    def _connect_to_api(self: PstDspComponentManager) -> None:
        """Establish connection to API component."""
        super()._connect_to_api()
        if self._disk_monitor_task is None:
            self._create_disk_monitor_task()

        self._disk_monitor_task.start_monitoring()  # type: ignore

    def _disconnect_from_api(self: PstDspComponentManager) -> None:
        """Disconnect from API component."""
        if self._disk_monitor_task is not None:
            self._disk_monitor_task.stop_monitoring(timeout=1.0)
            self._disk_monitor_task = None

        super()._disconnect_from_api()

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

    def _get_disk_stats_from_api(self: PstDspComponentManager, *args: Any, **kwargs: Any) -> None:
        """
        Update the disk usage details calling API.

        This gets the `disk_capacity` and `available_disk_space` from the API via
        calling the :py:meth:`ProcessApi.get_env` method.

        This is used to get the value of the disk capacity and the  available disk
        space before the DSP.DISK starts monitoring. This is needed as BEAM.MGMT
        needs to know the value before we monitor.
        """
        environment_values = self._api.get_env()
        try:
            self._monitor_data_store.update_disk_stats(**environment_values)
            self._monitor_data_handler.update_monitor_data(notify=False)

            for k, v in environment_values.items():
                self._property_callback(k, v)
        except Exception:
            self.logger.warning(
                f"Failure to get disk stats from API. environment_values={environment_values}", exc_info=True
            )
            raise

    def validate_configure_scan(
        self: PstDspComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Validate a ConfigureScan request sent from CSP.LMC to the DSP sub-component.

        This asserts the request can be converted to DSP resources and then calls the process API to perform
        the validation.

        :param configuration: configuration that would be used when the configure_beam and configure_scan
            methods are called.
        :type configuration: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """

        def _task(task_callback: Callable) -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            try:
                dsp_resources = calculate_dsp_subband_resources(self.beam_id, request_params=configuration)

                self._api.validate_configure_beam(configuration=dsp_resources[1])
                self._api.validate_configure_scan(configuration=configuration)
                task_callback(status=TaskStatus.COMPLETED, result="Completed")
            except Exception as e:
                task_callback(status=TaskStatus.FAILED, exception=e)

        return self._submit_background_task(_task, task_callback=task_callback)

    def configure_beam(
        self: PstDspComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure the beam of the the component with the resources.

        :param configuration: parameters to be configured and their requested values
        """
        dsp_resources = calculate_dsp_subband_resources(self.beam_id, request_params=configuration)

        # deal only with subband 1 for now.
        self.logger.debug(f"Submitting API with dsp_resources={dsp_resources[1]}")

        def _task(task_callback: Callback = None) -> None:
            self._api.configure_beam(
                configuration=dsp_resources[1], task_callback=wrap_callback(task_callback)
            )
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
                polling_rate=self.monitoring_polling_rate,
            )

        return self._submit_background_task(_task, task_callback=task_callback)

    def stop_scan(self: PstDspComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning."""

        def _task(task_callback: Callback = None) -> None:
            self._api.stop_scan(task_callback=wrap_callback(task_callback))

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
