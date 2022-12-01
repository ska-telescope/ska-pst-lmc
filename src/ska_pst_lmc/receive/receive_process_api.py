# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the API to be communicate with the RECV process.

The :py:class:`PstReceiveProcessApiSimulator` is used in testing or
simulation mode, while the :py:class:`PstReceiveProcessApiGrpc` is used
to connect to a remote application that exposes a gRPC API.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Generator, Optional

from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    BeamConfiguration,
    MonitorData,
    ReceiveBeamConfiguration,
    ReceiveMonitorData,
    ReceiveScanConfiguration,
    ReceiveSubbandResources,
    ScanConfiguration,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component.process_api import PstProcessApi, PstProcessApiGrpc, PstProcessApiSimulator
from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator
from ska_pst_lmc.util.background_task import BackgroundTask, BackgroundTaskProcessor, background_task

from .receive_util import generate_recv_scan_request

__all__ = [
    "PstReceiveProcessApi",
    "PstReceiveProcessApiSimulator",
    "PstReceiveProcessApiGrpc",
]


GIGABITS_PER_BYTE = 8 / 1e9
"""Scale factor used to calculated gigabits from a number of bytes."""


class PstReceiveProcessApi(PstProcessApi):
    """Abstract class for the API of the RECV process.

    This extends from :py:class:`PstProcessApi` but
    provides the specific method of getting the monitoring
    data.
    """


class PstReceiveProcessApiSimulator(PstProcessApiSimulator, PstReceiveProcessApi):
    """A simulator implemenation version of the  API of `PstReceiveProcessApi`."""

    def __init__(
        self: PstReceiveProcessApiSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
        simulator: Optional[PstReceiveSimulator] = None,
    ) -> None:
        """Initialise the API.

        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        :param simulator: the simulator instance to use in the API.
        """
        self._simulator = simulator or PstReceiveSimulator()
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self._communication_task: Optional[BackgroundTask] = None
        self.data: Optional[ReceiveData] = None

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def configure_beam(
        self: PstReceiveProcessApiSimulator, resources: Dict[str, Any], task_callback: Callable
    ) -> None:
        """Configure beam for the service.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=33)
        time.sleep(0.01)
        task_callback(progress=66)
        time.sleep(0.01)
        self._component_state_callback(resourced=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure_beam(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Deconfigure the beam.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=50)
        time.sleep(0.01)
        self._component_state_callback(resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def configure_scan(
        self: PstReceiveProcessApiSimulator, configuration: Dict[str, Any], task_callback: Callable
    ) -> None:
        """Configure a scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=30)
        time.sleep(0.01)
        task_callback(progress=60)
        self._simulator.configure_scan(configuration=configuration)
        time.sleep(0.01)
        self._component_state_callback(configured=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure_scan(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Deconfigure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=31)
        time.sleep(0.01)
        task_callback(progress=89)
        time.sleep(0.01)
        self._simulator.deconfigure_scan()
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def start_scan(
        self: PstReceiveProcessApiSimulator, args: Dict[str, Any], task_callback: Callable
    ) -> None:
        """Start scanning.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=27)
        time.sleep(0.01)
        task_callback(progress=69)
        self._simulator.start_scan(args)
        self._component_state_callback(scanning=True)
        self._scanning = True
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def stop_scan(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=32)
        time.sleep(0.01)
        task_callback(progress=88)
        self._simulator.stop_scan()
        self._component_state_callback(scanning=False)
        self._scanning = False
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    @background_task
    def abort(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=60)
        self._component_state_callback(scanning=False)
        self._simulator.abort()
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def reset(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Reset a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.01)
        task_callback(progress=47)
        self._component_state_callback(configured=False)
        self._simulator.reset()
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def _simulated_monitor_data_generator(
        self: PstReceiveProcessApiSimulator, polling_rate: int
    ) -> Generator[Dict[int, Any], None, None]:
        while self._scanning:
            self._logger.debug("Background generator is creating data")
            yield self._simulator.get_subband_data()
            self._logger.debug(f"Sleeping {polling_rate}ms")
            time.sleep(polling_rate / 1000.0)

    def get_env(self: PstReceiveProcessApiSimulator) -> Dict[str, Any]:
        """Get simulated environment values for RECV.CORE.

        This returns the following:

        * data_host = '127.0.0.1'
        * data_port = 32080
        """
        return {
            "data_host": "127.0.0.1",
            "data_port": 32080,
        }


class PstReceiveProcessApiGrpc(PstProcessApiGrpc, PstReceiveProcessApi):
    """This is an gRPC implementation of the `PstReceiveProcessApi`.

    This uses an instance of a `PstGrpcLmcClient` to send requests through
    to the RECV.CORE application. Instances of this class should be per
    subband, rather than one for all of RECV as a whole.
    """

    def _get_configure_beam_request(
        self: PstReceiveProcessApiGrpc, resources: Dict[str, Any]
    ) -> BeamConfiguration:
        subband_resources = ReceiveSubbandResources(**resources["subband"])
        return BeamConfiguration(
            receive=ReceiveBeamConfiguration(subband_resources=subband_resources, **resources["common"])
        )

    def _get_configure_scan_request(
        self: PstReceiveProcessApiGrpc, configure_parameters: Dict[str, Any]
    ) -> ScanConfiguration:
        return ScanConfiguration(
            receive=ReceiveScanConfiguration(**generate_recv_scan_request(configure_parameters))
        )

    def _handle_monitor_response(
        self: PstProcessApiGrpc, data: MonitorData, monitor_data_callback: Callable[..., None]
    ) -> None:
        receive_monitor_data: ReceiveMonitorData = data.receive
        monitor_data_callback(
            subband_id=1,
            subband_data=ReceiveData(
                received_data=receive_monitor_data.data_received,
                data_receive_rate=receive_monitor_data.receive_rate * GIGABITS_PER_BYTE,
                dropped_data=receive_monitor_data.data_dropped,
                dropped_rate=receive_monitor_data.data_drop_rate,
                misordered_packets=receive_monitor_data.misordered_packets,
            ),
        )
