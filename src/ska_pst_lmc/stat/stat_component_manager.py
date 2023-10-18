# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides an implementation of the STAT PST component manager."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, Optional

from ska_tango_base.control_model import PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import (
    MonitorDataHandler,
    PstApiComponentManager,
    PstApiDeviceInterface,
    TaskResponse,
)
from ska_pst_lmc.stat.stat_model import StatMonitorData, StatMonitorDataStore
from ska_pst_lmc.stat.stat_process_api import (
    PstStatProcessApi,
    PstStatProcessApiGrpc,
    PstStatProcessApiSimulator,
)
from ska_pst_lmc.stat.stat_util import calculate_stat_subband_resources
from ska_pst_lmc.util.callback import Callback, wrap_callback

__all__ = ["PstStatComponentManager"]


class PstStatComponentManager(PstApiComponentManager[StatMonitorData, PstStatProcessApi]):
    """Component manager for the STAT component for the PST.LMC subsystem."""

    def __init__(
        self: PstStatComponentManager,
        *,
        device_interface: PstApiDeviceInterface[StatMonitorData],
        logger: logging.Logger,
        api: Optional[PstStatProcessApi] = None,
        **kwargs: Any,
    ):
        """
        Initialise instance of the component manager.

        :param device_interface: an abstract view of the TANGO device. This allows for updating properties on
            the device without having to have the device class itself.
        :param logger: a logger for this object is to use.
        :param api: the API to use for interacting with STAT.  This is optional
        """
        logger.debug(
            f"Setting up STAT component manager with device_name='{device_interface.device_name}'"
            + f"and api_endpoint='{device_interface.process_api_endpoint}'"
        )
        api = api or PstStatProcessApiSimulator(
            logger=logger,
            component_state_callback=device_interface.handle_component_state_change,
        )

        # Set up handling of monitor data.
        self._monitor_data_handler = MonitorDataHandler(
            data_store=StatMonitorDataStore(),
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
    def real_pol_a_mean_freq_avg(self: PstStatComponentManager) -> float:
        """Get the mean of the real data for pol A, averaged over all channels."""
        return self._monitor_data.real_pol_a_mean_freq_avg

    @property
    def real_pol_a_variance_freq_avg(self: PstStatComponentManager) -> float:
        """Get the variance of the real data for pol A, averaged over all channels."""
        return self._monitor_data.real_pol_a_variance_freq_avg

    @property
    def real_pol_a_num_clipped_samples(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the real data for pol A."""
        return self._monitor_data.real_pol_a_num_clipped_samples

    @property
    def imag_pol_a_mean_freq_avg(self: PstStatComponentManager) -> float:
        """Get the mean of the imaginary data for pol A, averaged over all channels."""
        return self._monitor_data.imag_pol_a_mean_freq_avg

    @property
    def imag_pol_a_variance_freq_avg(self: PstStatComponentManager) -> float:
        """Get the variance of the imaginary data for pol A, averaged over all channels."""
        return self._monitor_data.imag_pol_a_variance_freq_avg

    @property
    def imag_pol_a_num_clipped_samples(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the imaginary data for pol A."""
        return self._monitor_data.imag_pol_a_num_clipped_samples

    @property
    def real_pol_a_mean_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the mean of the real data for pol A, averaged over channels without RFI."""
        return self._monitor_data.real_pol_a_mean_freq_avg_rfi_excised

    @property
    def real_pol_a_variance_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the variance of the real data for pol A, averaged over channels without RFI."""
        return self._monitor_data.real_pol_a_variance_freq_avg_rfi_excised

    @property
    def real_pol_a_num_clipped_samples_rfi_excised(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the real data for pol A in channels without RFI."""
        return self._monitor_data.real_pol_a_num_clipped_samples_rfi_excised

    @property
    def imag_pol_a_mean_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the mean of the imaginary data for pol A, averaged over channels without RFI."""
        return self._monitor_data.imag_pol_a_mean_freq_avg_rfi_excised

    @property
    def imag_pol_a_variance_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the variance of the imaginary data for pol A, averaged over channels without RFI."""
        return self._monitor_data.imag_pol_a_variance_freq_avg_rfi_excised

    @property
    def imag_pol_a_num_clipped_samples_rfi_excised(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the imaginary data for pol A in channels without RFI."""
        return self._monitor_data.imag_pol_a_num_clipped_samples_rfi_excised

    @property
    def real_pol_b_mean_freq_avg(self: PstStatComponentManager) -> float:
        """Get the mean of the real data for pol B, averaged over all channels."""
        return self._monitor_data.real_pol_b_mean_freq_avg

    @property
    def real_pol_b_variance_freq_avg(self: PstStatComponentManager) -> float:
        """Get the variance of the real data for pol B, averaged over all channels."""
        return self._monitor_data.real_pol_b_variance_freq_avg

    @property
    def real_pol_b_num_clipped_samples(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the real data for pol B."""
        return self._monitor_data.real_pol_b_num_clipped_samples

    @property
    def imag_pol_b_mean_freq_avg(self: PstStatComponentManager) -> float:
        """Get the mean of the imaginary data for pol B, averaged over all channels."""
        return self._monitor_data.imag_pol_b_mean_freq_avg

    @property
    def imag_pol_b_variance_freq_avg(self: PstStatComponentManager) -> float:
        """Get the variance of the imaginary data for pol B, averaged over all channels."""
        return self._monitor_data.imag_pol_b_variance_freq_avg

    @property
    def imag_pol_b_num_clipped_samples(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the imaginary data for pol B."""
        return self._monitor_data.imag_pol_b_num_clipped_samples

    @property
    def real_pol_b_mean_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the mean of the real data for pol B, averaged over channels without RFI."""
        return self._monitor_data.real_pol_b_mean_freq_avg_rfi_excised

    @property
    def real_pol_b_variance_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the variance of the real data for pol B, averaged over channels without RFI."""
        return self._monitor_data.real_pol_b_variance_freq_avg_rfi_excised

    @property
    def real_pol_b_num_clipped_samples_rfi_excised(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the real data for pol B in channels without RFI."""
        return self._monitor_data.real_pol_b_num_clipped_samples_rfi_excised

    @property
    def imag_pol_b_mean_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the mean of the imaginary data for pol B, averaged over channels without RFI."""
        return self._monitor_data.imag_pol_b_mean_freq_avg_rfi_excised

    @property
    def imag_pol_b_variance_freq_avg_rfi_excised(self: PstStatComponentManager) -> float:
        """Get the variance of the imaginary data for pol B, averaged over channels without RFI."""
        return self._monitor_data.imag_pol_b_variance_freq_avg_rfi_excised

    @property
    def imag_pol_b_num_clipped_samples_rfi_excised(self: PstStatComponentManager) -> int:
        """Get the num of clipped samples of the imaginary data for pol B in channels without RFI."""
        return self._monitor_data.imag_pol_b_num_clipped_samples_rfi_excised

    @property
    def _monitor_data(self: PstStatComponentManager) -> StatMonitorData:
        """Get monitor data from data handler."""
        return self._monitor_data_handler.monitor_data

    def _update_api(self: PstStatComponentManager) -> None:
        """Update instance of API based on simulation mode."""
        if self._simuation_mode == SimulationMode.TRUE:
            self._api = PstStatProcessApiSimulator(
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )
        else:
            self._api = PstStatProcessApiGrpc(
                client_id=self.device_name,
                grpc_endpoint=self.api_endpoint,
                logger=self.logger,
                component_state_callback=self._push_component_state_update,
            )

    def validate_configure_scan(
        self: PstStatComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Validate a ConfigureScan request sent from CSP.LMC to the STAT sub-component.

        This asserts the request can be converted to STAT resources and then calls the process API to perform
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
                stat_resources = calculate_stat_subband_resources(self.beam_id, request_params=configuration)

                self._api.validate_configure_beam(configuration=stat_resources[1])
                self._api.validate_configure_scan(configuration=configuration)
                task_callback(status=TaskStatus.COMPLETED, result="Completed")
            except Exception as e:
                self.logger.exception(
                    f"Failed to validate scan configuration for {self.device_name}.", exc_info=True
                )
                task_callback(status=TaskStatus.FAILED, exception=e)

        return self._submit_background_task(_task, task_callback=task_callback)

    def configure_beam(
        self: PstStatComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure beam resources in the component.

        :param configuration: parameters to be configured and their requested values.
        """
        stat_resources = calculate_stat_subband_resources(self.beam_id, request_params=configuration)

        # deal only with subband 1 for now.
        self.logger.debug(f"Submitting API with stat_resources={stat_resources[1]}")

        return self._submit_background_task(
            functools.partial(self._api.configure_beam, configuration=stat_resources[1]),
            task_callback=task_callback,
        )

    def start_scan(
        self: PstStatComponentManager, args: Dict[str, Any], task_callback: Callback = None
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

    def stop_scan(self: PstStatComponentManager, task_callback: Callback = None) -> TaskResponse:
        """End scanning."""

        def _task(task_callback: Callback = None) -> None:
            self._api.stop_scan(task_callback=wrap_callback(task_callback))

            # reset the monitoring data
            self._monitor_data_handler.reset_monitor_data()

        return self._submit_background_task(_task, task_callback=task_callback)
