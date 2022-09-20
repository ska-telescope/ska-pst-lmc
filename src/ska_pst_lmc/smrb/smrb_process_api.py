# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the API to be communicate with the SMRB process.

The :py:class:`PstSmrbProcessApiSimulator` is used in testing or
simulation.)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Generator, Optional

from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    MonitorData,
    ResourceConfiguration,
    ScanConfiguration,
    SmrbResources,
    SmrbScanConfiguration,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component.process_api import PstProcessApi, PstProcessApiGrpc, PstProcessApiSimulator
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData, SubbandMonitorData
from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor

__all__ = [
    "PstSmrbProcessApi",
    "PstSmrbProcessApiSimulator",
    "PstSmrbProcessApiGrpc",
]


class PstSmrbProcessApi(PstProcessApi):
    """Abstract class for the API of the SMRB process.

    This extends from :py:class:`PstProcessApi` but
    provides the specific method of getting the monitoring
    data.
    """


class PstSmrbProcessApiSimulator(PstProcessApiSimulator, PstSmrbProcessApi):
    """A simulator implemenation version of the  API of `PstSmrbProcessApi`."""

    def __init__(
        self: PstSmrbProcessApiSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
        simulator: Optional[PstSmrbSimulator] = None,
    ) -> None:
        """Initialise the API.

        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        :param simulator: the simulator instance to use in the API.
        """
        self._simulator = simulator or PstSmrbSimulator()
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self.data: Optional[SmrbMonitorData] = None

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def assign_resources(self: PstSmrbProcessApiSimulator, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        self._logger.info(f"Assigning resources for SMRB. {resources}")
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=50)
        time.sleep(0.1)
        self._component_state_callback(resourced=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def release_resources(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=45)
        time.sleep(0.1)
        self._component_state_callback(resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def configure(self: PstSmrbProcessApiSimulator, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=42)
        time.sleep(0.1)
        task_callback(progress=58)
        self._simulator.configure(configuration=configuration)
        time.sleep(0.1)
        self._component_state_callback(configured=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=20)
        time.sleep(0.05)
        task_callback(progress=50)
        time.sleep(0.05)
        task_callback(progress=80)
        time.sleep(0.1)
        self._simulator.deconfigure()
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def scan(self: PstSmrbProcessApiSimulator, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=55)
        time.sleep(0.1)
        self._simulator.scan(args)
        self._component_state_callback(scanning=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def end_scan(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=37)
        time.sleep(0.1)
        task_callback(progress=63)
        self._simulator.end_scan()
        self._component_state_callback(scanning=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def abort(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._simulator.abort()
        time.sleep(0.1)
        task_callback(progress=59)
        self._component_state_callback(scanning=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def reset(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=37)
        time.sleep(0.1)
        task_callback(progress=63)
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def restart(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=40)
        time.sleep(0.1)
        task_callback(progress=62)
        self._component_state_callback(configured=False, resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def _simulated_monitor_data_generator(
        self: PstSmrbProcessApiSimulator, polling_rate: int
    ) -> Generator[Dict[int, Any], None, None]:
        while True:
            self._logger.debug("Background generator is creating data")
            yield self._simulator.get_subband_data()
            self._logger.debug(f"Sleeping {polling_rate}ms")
            time.sleep(polling_rate / 1000.0)


class PstSmrbProcessApiGrpc(PstProcessApiGrpc, PstSmrbProcessApi):
    """This is an gRPC implementation of the `PstSmrbProcessApi` API.

    This uses an instance of a `PstGrpcLmcClient` to send requests through
    to the SMRB.RB application. Instances of this class should be per
    subband, rather than one for all of RECV as a whole.
    """

    def _get_assign_resources_request(self: PstSmrbProcessApiGrpc, resources: dict) -> ResourceConfiguration:
        return ResourceConfiguration(smrb=SmrbResources(**resources))

    def _handle_monitor_response(
        self: PstSmrbProcessApiGrpc, data: MonitorData, monitor_data_callback: Callable[..., None]
    ) -> None:
        smrb_data_stats = data.smrb.data
        smrb_weights_stats = data.smrb.weights

        # assume the number of written and read are the same for data and weights
        # so total written/read size in bytes is the total buffer size * written/read
        buffer_size = smrb_data_stats.bufsz + smrb_weights_stats.bufsz
        total_written = buffer_size * smrb_data_stats.written
        total_read = buffer_size * smrb_data_stats.read

        monitor_data_callback(
            subband_id=1,
            subband_data=SubbandMonitorData(
                buffer_size=buffer_size,
                total_written=total_written,
                total_read=total_read,
                full=smrb_data_stats.full,
                num_of_buffers=smrb_data_stats.nbufs,
            ),
        )

    def _get_configure_scan_request(self: PstProcessApiGrpc, configure_parameters: dict) -> ScanConfiguration:
        return ScanConfiguration(smrb=SmrbScanConfiguration())
