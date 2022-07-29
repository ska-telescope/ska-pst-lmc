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
import threading
import time
from typing import Callable, Dict, Generator, Optional

from ska_pst_lmc_proto.ska_pst_lmc_pb2 import AssignResourcesRequest, SmrbResources
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component.grpc_lmc_client import (
    AlreadyScanningException,
    BaseGrpcException,
    NotScanningException,
    PstGrpcLmcClient,
    ResourcesAlreadyAssignedException,
    ResourcesNotAssignedException,
)
from ska_pst_lmc.component.process_api import PstProcessApi
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData, SubbandMonitorData
from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor, background_task
from ska_pst_lmc.util.timeout_iterator import TimeoutIterator

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

    @background_task
    def monitor(
        self: PstSmrbProcessApi,
        subband_monitor_data_callback: Callable[..., None],
        polling_rate: int = 5000,
        monitor_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """Monitor data of remote service.

        This needs to be implemented as a background task

        :param subband_monitor_data_callback: callback to use when there is an
            update of the sub-band monitor data.
        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param monitor_abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring. If not set then the background task
            will create one.
        """
        raise NotImplementedError("PstSmrbProcessApi is abstract class")


class PstSmrbProcessApiSimulator(PstSmrbProcessApi):
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
        self._monitor_abort_event: Optional[threading.Event] = None

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def connect(self: PstSmrbProcessApiSimulator) -> None:
        """Connect to the external process."""

    def disconnect(self: PstSmrbProcessApiSimulator) -> None:
        """Disconnect from the external process."""
        if self._monitor_abort_event is not None:
            self._monitor_abort_event.set()

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

    @background_task
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

    @background_task
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

    @background_task
    def abort(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=59)
        self._component_state_callback(scanning=False)
        self._simulator.abort()
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    @background_task
    def monitor(
        self: PstSmrbProcessApiSimulator,
        subband_monitor_data_callback: Callable[..., None],
        polling_rate: int = 5000,
        monitor_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """Monitor data of remote service.

        This needs to be implemented as a background task

        :param subband_monitor_data_callback: callback to use when there is an
            update of the sub-band monitor data.
        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param monitor_abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring. If not set then the background task
            will create one.
        """
        self._logger.debug(f"Starting to monitor at {polling_rate}")
        try:
            if monitor_abort_event is None:
                self._monitor_abort_event = threading.Event()
            else:
                self._monitor_abort_event = monitor_abort_event

            def _generator() -> Generator[Dict[int, SubbandMonitorData], None, None]:
                while True:
                    self._logger.debug("Background generator is creating data")
                    yield self._simulator.get_subband_data()
                    self._logger.debug(f"Sleeping {polling_rate}ms")
                    time.sleep(polling_rate / 1000.0)

            for data in TimeoutIterator(
                _generator(),
                abort_event=self._monitor_abort_event,
                timeout=2 * polling_rate / 1000.0,
                expected_rate=polling_rate / 1000.0,
            ):
                for (subband_id, subband_data) in data.items():
                    subband_monitor_data_callback(subband_id=subband_id, subband_data=subband_data)
        except Exception:
            self._logger.error("error while monitoring.", exc_info=True)


class PstSmrbProcessApiGrpc(PstSmrbProcessApi):
    """An interface for the gRPC implemenation version of the  API of `PstSmrbProcessApi`.

    At the moment this performs the same as the `PstSmrbProcessApiSimulator` but as
    the gRPC service is implemented this functionality will be migrated across.
    """

    def __init__(
        self: PstSmrbProcessApiGrpc,
        client_id: str,
        grpc_endpoint: str,
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
        logger.info("Creating instance of gRPC Process API")
        self._grpc_client = PstGrpcLmcClient(client_id=client_id, endpoint=grpc_endpoint, logger=logger)
        self._simulator = simulator or PstSmrbSimulator()
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self._monitor_abort_event: Optional[threading.Event] = None
        self._connected = False

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def connect(self: PstSmrbProcessApiGrpc) -> None:
        """Connect to the external process.

        Connects to the remote gRPC service. It also establishes a
        """
        self._logger.info("About to call gRPC client connect")
        self._connected = self._grpc_client.connect()

    def disconnect(self: PstSmrbProcessApiGrpc) -> None:
        """Disconnect from the external process."""
        if self._monitor_abort_event is not None:
            self._monitor_abort_event.set()

    def assign_resources(self: PstSmrbProcessApiGrpc, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        self._logger.info(f"Assigning resources for SMRB. {resources}")
        task_callback(status=TaskStatus.IN_PROGRESS)

        smrb_resources = SmrbResources(**resources)
        request = AssignResourcesRequest(smrb=smrb_resources)
        try:
            self._grpc_client.assign_resources(request=request)

            self._component_state_callback(resourced=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ResourcesAlreadyAssignedException as e:
            self._logger.error(e.message)
            task_callback(result=e.message, status=TaskStatus.FAILED)
        except BaseGrpcException as e:
            self._logger.error("Problem processing assign_resources request for SMRB.", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message)

    def release_resources(self: PstSmrbProcessApiGrpc, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            self._grpc_client.release_resources()

            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ResourcesNotAssignedException as e:
            self._logger.warning(e.message)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result=e.message)
        except BaseGrpcException as e:
            self._logger.error("Problem processing release_resources request for SMRB.", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message)

    def configure(self: PstSmrbProcessApiGrpc, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        For SMRB this is a no-op command. There is nothing on the server that would be
        performed and executing this will do nothing.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._component_state_callback(configured=True)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def deconfigure(self: PstSmrbProcessApiGrpc, task_callback: Callable) -> None:
        """Deconfiure a scan.

        For SMRB this is a no-op command. There is nothin on the server that would be
        performed and executing this will do nothing.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def scan(
        self: PstSmrbProcessApiGrpc,
        args: dict,
        task_callback: Callable,
    ) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._grpc_client.scan()
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except AlreadyScanningException as e:
            self._logger.warning(e.message)
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error("Problem processing scan request for SMRB.", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message)

    def end_scan(self: PstSmrbProcessApiGrpc, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._stop_monitoring()
            self._grpc_client.end_scan()
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except NotScanningException as e:
            self._logger.warning(e.message)
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error("Problem processing end_scan request for SMRB.", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message)

    @background_task
    def abort(self: PstSmrbProcessApiGrpc, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=59)
        self._component_state_callback(scanning=False)
        self._simulator.abort()
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    def _stop_monitoring(self: PstSmrbProcessApiGrpc) -> None:
        if self._monitor_abort_event is not None:
            self._monitor_abort_event.set()

    @background_task
    def monitor(
        self: PstSmrbProcessApiGrpc,
        subband_monitor_data_callback: Callable[..., None],
        polling_rate: int = 5000,
        monitor_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """Monitor data of remote service.

        :param subband_monitor_data_callback: callback to use when there is an
            update of the sub-band monitor data.
        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param monitor_abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring. If not set then the background task
            will create one.
        """
        self._logger.debug(f"Starting to monitor at {polling_rate}")
        self._monitor_abort_event = monitor_abort_event or threading.Event()
        try:
            for d in self._grpc_client.monitor(
                polling_rate=polling_rate, abort_event=self._monitor_abort_event
            ):
                assert d.has_smrb(), "Expected SMRB field in monitor data"
                smrb_data_stats = d.smrb.data_stats
                smrb_weights_stats = d.smrb.weights_stats

                # assume the number of written and read are the same for data and weights
                # so total written/read size in bytes is the total buffer size * written/read
                buffer_size = smrb_data_stats.bufsz + smrb_weights_stats.bufsz
                total_written = buffer_size * smrb_data_stats.written
                total_read = buffer_size * smrb_data_stats.read

                subband_monitor_data_callback(
                    data=SubbandMonitorData(
                        buffer_size=buffer_size,
                        total_written=total_written,
                        total_read=total_read,
                        full=smrb_data_stats.full,
                        num_of_buffers=smrb_data_stats.nbufs,
                    )
                )
        except Exception:
            pass
