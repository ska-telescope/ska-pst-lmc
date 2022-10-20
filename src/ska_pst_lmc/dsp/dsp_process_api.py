# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the API to be communicate with the DSP process.

The :py:class:`PstDsprocessApiSimulator` is used in testing or
simulation mode, while the :py:class:`PstDspProcessApiGrpc` is used
to connect to a remote application that exposes a gRPC API.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Generator, Optional

from ska_pst_lmc_proto.ska_pst_lmc_pb2 import DspMonitorData as DspMonitorDataProtobuf
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    DspResources,
    DspScanConfiguration,
    MonitorData,
    ResourceConfiguration,
    ScanConfiguration,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component.process_api import PstProcessApiGrpc, PstProcessApiSimulator
from ska_pst_lmc.dsp.dsp_model import DspMonitorData, DspSubbandMonitorData
from ska_pst_lmc.dsp.dsp_simulator import PstDspSimulator
from ska_pst_lmc.dsp.dsp_util import generate_dsp_scan_request
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor

__all__ = [
    "PstDspProcessApi",
    "PstDspProcessApiSimulator",
]

from ska_pst_lmc.component import PstProcessApi


class PstDspProcessApi(PstProcessApi):
    """Abstract class for the API of the DSP process.

    This extends from :py:class:`PstProcessApi` but
    provides the specific method of getting the monitoring
    data.
    """


class PstDspProcessApiSimulator(PstProcessApiSimulator, PstDspProcessApi):
    """A simulator implemenation version of the  API of `PstDspProcessApi`."""

    def __init__(
        self: PstDspProcessApiSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
        simulator: Optional[PstDspSimulator] = None,
    ) -> None:
        """Initialise the API.

        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        :param simulator: the simulator instance to use in the API.
        """
        self._simulator = simulator or PstDspSimulator()
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self.data: Optional[DspMonitorData] = None

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def configure_beam(self: PstDspProcessApiSimulator, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        self._logger.info(f"Assigning resources for DSP. {resources}")
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=42)
        time.sleep(0.1)
        self._component_state_callback(resourced=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure_beam(self: PstDspProcessApiSimulator, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=48)
        time.sleep(0.1)
        self._component_state_callback(resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def configure_scan(self: PstDspProcessApiSimulator, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=35)
        time.sleep(0.1)
        task_callback(progress=81)
        self._simulator.configure_scan(configuration=configuration)
        time.sleep(0.1)
        self._component_state_callback(configured=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure_scan(self: PstDspProcessApiSimulator, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=22)
        time.sleep(0.05)
        task_callback(progress=56)
        time.sleep(0.05)
        task_callback(progress=76)
        time.sleep(0.1)
        self._simulator.deconfigure_scan()
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def start_scan(self: PstDspProcessApiSimulator, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=59)
        time.sleep(0.1)
        self._simulator.start_scan(args)
        self._component_state_callback(scanning=True)
        self._scanning = True
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def stop_scan(self: PstDspProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=31)
        time.sleep(0.1)
        task_callback(progress=77)
        self._simulator.stop_scan()
        self._component_state_callback(scanning=False)
        self._scanning = False
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def abort(self: PstDspProcessApiSimulator, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._simulator.abort()
        time.sleep(0.1)
        task_callback(progress=64)
        self._component_state_callback(scanning=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def reset(self: PstDspProcessApiSimulator, task_callback: Callable) -> None:
        """Reset service when in ABORTED / FAULT state.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=37)
        time.sleep(0.1)
        task_callback(progress=63)
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def restart(self: PstDspProcessApiSimulator, task_callback: Callable) -> None:
        """Restart service when in ABORTED / FAULT state.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=47)
        time.sleep(0.1)
        task_callback(progress=87)
        self._component_state_callback(configured=False, resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def _simulated_monitor_data_generator(
        self: PstDspProcessApiSimulator, polling_rate: int
    ) -> Generator[Dict[int, Any], None, None]:
        while self._scanning:
            self._logger.debug("Background generator is creating data")
            yield self._simulator.get_subband_data()
            self._logger.debug(f"Sleeping {polling_rate}ms")
            time.sleep(polling_rate / 1000.0)


class PstDspProcessApiGrpc(PstProcessApiGrpc, PstDspProcessApi):
    """This is an gRPC implementation of the `PstDspProcessApi` API.

    This uses an instance of a `PstGrpcLmcClient` to send requests through
    to the DSP.CORE application. Instances of this class should be per
    subband, rather than one for all of RECV as a whole.
    """

    def _get_configure_beam_request(self: PstDspProcessApiGrpc, resources: dict) -> ResourceConfiguration:
        return ResourceConfiguration(dsp=DspResources(**resources))

    def _handle_monitor_response(
        self: PstDspProcessApiGrpc, data: MonitorData, monitor_data_callback: Callable[..., None]
    ) -> None:
        dsp_data: DspMonitorDataProtobuf = data.dsp

        monitor_data_callback(
            subband_id=1,
            subband_data=DspSubbandMonitorData(
                disk_capacity=dsp_data.disk_capacity,
                disk_available_bytes=dsp_data.disk_available_bytes,
                bytes_written=dsp_data.bytes_written,
                write_rate=dsp_data.write_rate,
            ),
        )

    def _get_configure_scan_request(self: PstProcessApiGrpc, configure_parameters: dict) -> ScanConfiguration:
        return ScanConfiguration(
            dsp=DspScanConfiguration(**generate_dsp_scan_request(request_params=configure_parameters))
        )
