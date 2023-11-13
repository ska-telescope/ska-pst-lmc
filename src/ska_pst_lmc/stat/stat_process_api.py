# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""
Module for providing the API to be communicate with the STAT process.

The :py:class:`PstStatProcessApiSimulator` is used in testing or
simulation.)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Generator, Optional

import numpy as np
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    BeamConfiguration,
    MonitorData,
    ScanConfiguration,
    StatBeamConfiguration,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import StatMonitorData as StatMonitorDataProto
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import StatScanConfiguration
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component import SUBBAND_1
from ska_pst_lmc.component.process_api import PstProcessApi, PstProcessApiGrpc, PstProcessApiSimulator
from ska_pst_lmc.stat.stat_model import StatMonitorData
from ska_pst_lmc.stat.stat_simulator import PstStatSimulator
from ska_pst_lmc.stat.stat_util import generate_stat_scan_request
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor

__all__ = [
    "PstStatProcessApi",
    "PstStatProcessApiSimulator",
    "PstStatProcessApiGrpc",
]

POLA_IDX = 0
POLB_IDX = 1
REAL_IDX = 0
IMAG_IDX = 1


class PstStatProcessApi(PstProcessApi):
    """
    Abstract class for the API of the STAT process.

    This extends from :py:class:`PstProcessApi` but
    provides the specific method of getting the monitoring
    data.
    """


class PstStatProcessApiSimulator(PstProcessApiSimulator, PstStatProcessApi):
    """A simulator implemenation version of the  API of `PstStatProcessApi`."""

    def __init__(
        self: PstStatProcessApiSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
        simulator: Optional[PstStatSimulator] = None,
    ) -> None:
        """
        Initialise the API.

        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the component manager / TANGO
            device to deal with state model changes.
        :param simulator: the simulator instance to use in the API.
        """
        self._simulator = simulator or PstStatSimulator()
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self.data: Optional[StatMonitorData] = None

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def configure_beam(
        self: PstStatProcessApiSimulator, configuration: dict, task_callback: Callable
    ) -> None:
        """
        Configure beam resources.

        This method is effectively a no-op operation.

        :param configuration: dictionary of parameters to be configured and their requested values.
        :param task_callback: callable to connect back to the component manager.
        """
        self._logger.info(f"Configuring beam for STAT. {configuration}")
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=49)
        time.sleep(0.01)
        self._component_state_callback(resourced=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure_beam(self: PstStatProcessApiSimulator, task_callback: Callable) -> None:
        """
        Deconfigure the beam.

        This method is effectively a no-op operation.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=51)
        time.sleep(0.01)
        self._component_state_callback(resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def configure_scan(
        self: PstStatProcessApiSimulator, configuration: dict, task_callback: Callable
    ) -> None:
        """
        Configure a scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=41)
        time.sleep(0.01)
        task_callback(progress=59)
        self._simulator.configure_scan(configuration=configuration)
        time.sleep(0.01)
        self._component_state_callback(configured=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure_scan(self: PstStatProcessApiSimulator, task_callback: Callable) -> None:
        """
        Deconfigure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=22)
        time.sleep(0.01)
        task_callback(progress=52)
        time.sleep(0.01)
        task_callback(progress=82)
        time.sleep(0.01)
        self._simulator.deconfigure_scan()
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def start_scan(self: PstStatProcessApiSimulator, args: dict, task_callback: Callable) -> None:
        """
        Start scanning.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=54)
        time.sleep(0.01)
        self._simulator.start_scan(args)
        self._component_state_callback(scanning=True)
        self._scanning = True
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def stop_scan(self: PstStatProcessApiSimulator, task_callback: Callable) -> None:
        """
        End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        self.stop_monitoring()
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=38)
        time.sleep(0.01)
        task_callback(progress=62)
        self._simulator.stop_scan()
        self._component_state_callback(scanning=False)
        self._scanning = False
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def abort(self: PstStatProcessApiSimulator, task_callback: Callable) -> None:
        """
        Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        self.stop_monitoring()
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._simulator.abort()
        time.sleep(0.01)
        task_callback(progress=60)
        self._component_state_callback(scanning=False)
        self._scanning = False
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def reset(self: PstStatProcessApiSimulator, task_callback: Callable) -> None:
        """
        Reset service when in ABORTED / FAULT state.

        :param task_callback: callable to connect back to the component manager.
        """
        self.stop_monitoring()
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=39)
        time.sleep(0.01)
        task_callback(progress=61)
        self._component_state_callback(configured=False, resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def _simulated_monitor_data_generator(
        self: PstStatProcessApiSimulator, polling_rate: int
    ) -> Generator[Dict[int, Any], None, None]:
        while self._scanning:
            self._logger.debug("Background generator is creating data")
            yield self._simulator.get_subband_data()
            self._logger.debug(f"Sleeping {polling_rate}ms")
            time.sleep(polling_rate / 1000.0)


class PstStatProcessApiGrpc(PstProcessApiGrpc, PstStatProcessApi):
    """This is an gRPC implementation of the `PstStatProcessApi` API.

    This uses an instance of a `PstGrpcLmcClient` to send requests through
    to the STAT.CORE application. Instances of this class should be per
    subband, rather than one for all of STAT as a whole.
    """

    def _get_configure_beam_request(self: PstStatProcessApiGrpc, configuration: dict) -> BeamConfiguration:
        return BeamConfiguration(stat=StatBeamConfiguration(**configuration))

    def _handle_monitor_response(
        self: PstStatProcessApiGrpc, data: MonitorData, monitor_data_callback: Callable[..., None]
    ) -> None:
        stat_data_proto: StatMonitorDataProto = data.stat

        try:
            mean_frequency_avg = (
                np.array(stat_data_proto.mean_frequency_avg).reshape((2, 2)).astype(dtype=np.float32)
            )
            mean_frequency_avg_rfi_excised = (
                np.array(stat_data_proto.mean_frequency_avg_masked).reshape((2, 2)).astype(dtype=np.float32)
            )
            variance_frequency_avg = (
                np.array(stat_data_proto.variance_frequency_avg).reshape((2, 2)).astype(dtype=np.float32)
            )
            variance_frequency_avg_rfi_excised = (
                np.array(stat_data_proto.variance_frequency_avg_masked)
                .reshape((2, 2))
                .astype(dtype=np.float32)
            )
            num_clipped_samples = (
                np.array(stat_data_proto.num_clipped_samples).reshape((2, 2)).astype(dtype=np.int32)
            )
            num_clipped_samples_rfi_excised = (
                np.array(stat_data_proto.num_clipped_samples_masked).reshape((2, 2)).astype(dtype=np.int32)
            )
        except ValueError:
            # Ignoring monitoring update due to un-populated statistics
            return

        subband_data = StatMonitorData(
            # Pol A + I
            real_pol_a_mean_freq_avg=mean_frequency_avg[POLA_IDX][REAL_IDX],
            real_pol_a_variance_freq_avg=variance_frequency_avg[POLA_IDX][REAL_IDX],
            real_pol_a_num_clipped_samples=num_clipped_samples[POLA_IDX][REAL_IDX],
            # Pol A + I (RFI excised)
            real_pol_a_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[POLA_IDX][REAL_IDX],
            real_pol_a_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[POLA_IDX][REAL_IDX],
            real_pol_a_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[POLA_IDX][REAL_IDX],
            # Pol A + Q
            imag_pol_a_mean_freq_avg=mean_frequency_avg[POLA_IDX][IMAG_IDX],
            imag_pol_a_variance_freq_avg=variance_frequency_avg[POLA_IDX][IMAG_IDX],
            imag_pol_a_num_clipped_samples=num_clipped_samples[POLA_IDX][IMAG_IDX],
            # Pol A + Q (RFI excised)
            imag_pol_a_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[POLA_IDX][IMAG_IDX],
            imag_pol_a_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[POLA_IDX][IMAG_IDX],
            imag_pol_a_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[POLA_IDX][IMAG_IDX],
            # Pol B + I
            real_pol_b_mean_freq_avg=mean_frequency_avg[POLB_IDX][REAL_IDX],
            real_pol_b_variance_freq_avg=variance_frequency_avg[POLB_IDX][REAL_IDX],
            real_pol_b_num_clipped_samples=num_clipped_samples[POLB_IDX][REAL_IDX],
            # Pol B + I (RFI excised)
            real_pol_b_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[POLB_IDX][REAL_IDX],
            real_pol_b_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[POLB_IDX][REAL_IDX],
            real_pol_b_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[POLB_IDX][REAL_IDX],
            # Pol B + Q
            imag_pol_b_mean_freq_avg=mean_frequency_avg[POLB_IDX][IMAG_IDX],
            imag_pol_b_variance_freq_avg=variance_frequency_avg[POLB_IDX][IMAG_IDX],
            imag_pol_b_num_clipped_samples=num_clipped_samples[POLB_IDX][IMAG_IDX],
            # Pol B + Q (RFI excised)
            imag_pol_b_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[POLB_IDX][IMAG_IDX],
            imag_pol_b_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[POLB_IDX][IMAG_IDX],
            imag_pol_b_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[POLB_IDX][IMAG_IDX],
        )

        monitor_data_callback(
            subband_id=SUBBAND_1,
            subband_data=subband_data,
        )

    def _get_configure_scan_request(self: PstProcessApiGrpc, configure_parameters: dict) -> ScanConfiguration:
        return ScanConfiguration(
            stat=StatScanConfiguration(**generate_stat_scan_request(request_params=configure_parameters))
        )
