# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV API."""

from __future__ import annotations

import logging
import threading
import time
import unittest
from random import randint
from typing import Callable, Generator
from unittest.mock import ANY, MagicMock, call

import grpc
import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AssignResourcesRequest,
    AssignResourcesResponse,
    ConnectionRequest,
    ConnectionResponse,
    EndScanRequest,
    EndScanResponse,
    ErrorCode,
    MonitorResponse,
    ReleaseResourcesRequest,
    ReleaseResourcesResponse,
    ScanRequest,
    ScanResponse,
    SmrbMonitorData,
    SmrbResources,
    SmrbStatitics,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.smrb.smrb_model import SubbandMonitorData
from ska_pst_lmc.smrb.smrb_process_api import PstSmrbProcessApiGrpc, PstSmrbProcessApiSimulator
from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


@pytest.fixture
def component_state_callback() -> Callable:
    """Create a mock component state callback to test actions."""
    return MagicMock()


@pytest.fixture
def task_callback() -> Callable:
    """Create a mock component to validate task callbacks."""
    return MagicMock()


@pytest.fixture
def simulation_api(
    simulator: PstSmrbSimulator,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    background_task_processor: BackgroundTaskProcessor,
) -> PstSmrbProcessApiSimulator:
    """Create an instance of the Simluator API."""
    api = PstSmrbProcessApiSimulator(
        simulator=simulator, logger=logger, component_state_callback=component_state_callback
    )
    api._background_task_processor = background_task_processor

    return api


@pytest.fixture
def grpc_api(
    client_id: str,
    grpc_port: int,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
) -> PstSmrbProcessApiGrpc:
    """Fixture to create instance of a gRPC API with client."""
    return PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logger,
        component_state_callback=component_state_callback,
    )


@pytest.fixture
def simulator() -> PstSmrbSimulator:
    """Create instance of a simulator to be used within the API."""
    return PstSmrbSimulator()


@pytest.fixture
def subband_monitor_data_callback() -> MagicMock:
    """Create a callback that can be used for subband data monitoring."""
    return MagicMock()


def test_simulated_monitor_calls_callback(
    simulation_api: PstSmrbProcessApiSimulator,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""

    def _abort_monitor() -> None:
        logger.debug("Test sleeping 600ms")
        time.sleep(0.6)
        logger.debug("Aborting monitoring.")
        abort_event.set()

    abort_thread = threading.Thread(target=_abort_monitor, daemon=True)
    abort_thread.start()

    simulation_api.monitor(
        subband_monitor_data_callback=subband_monitor_data_callback,
        polling_rate=500,
        monitor_abort_event=abort_event,
    )
    abort_thread.join()
    logger.debug("Abort thread finished.")

    calls = [
        call(subband_id=subband_id, subband_data=subband_data)
        for (subband_id, subband_data) in simulation_api._simulator.get_subband_data().items()
    ]
    subband_monitor_data_callback.assert_has_calls(calls=calls)


def test_assign_resources(
    simulation_api: PstSmrbProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that assign resources simulator calls task."""
    resources: dict = {}

    simulation_api.assign_resources(resources, task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=50),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=True)


def test_release_resources(
    simulation_api: PstSmrbProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release resources simulator calls task."""
    simulation_api.release_resources(task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=45),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=False)


def test_configure(
    simulation_api: PstSmrbProcessApiSimulator,
    simulator: PstSmrbSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    configuration: dict = {"nchan": 512}

    with unittest.mock.patch.object(simulator, "configure", wraps=simulator.configure) as configure:
        simulation_api.configure(configuration, task_callback)
        configure.assert_called_with(configuration=configuration)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=42),
        call(progress=58),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=True)


def test_deconfigure(
    simulation_api: PstSmrbProcessApiSimulator,
    simulator: PstSmrbSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    with unittest.mock.patch.object(simulator, "deconfigure", wraps=simulator.deconfigure) as deconfigure:
        simulation_api.deconfigure(task_callback)
        deconfigure.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=20),
        call(progress=50),
        call(progress=80),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False)


def test_scan(
    simulation_api: PstSmrbProcessApiSimulator,
    simulator: PstSmrbSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    args = {"cat": "dog"}
    with unittest.mock.patch.object(simulator, "scan", wraps=simulator.scan) as scan:
        simulation_api.scan(args, task_callback)
        scan.assert_called_with(args)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=55),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=True)


def test_end_scan(
    simulation_api: PstSmrbProcessApiSimulator,
    simulator: PstSmrbSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that end_scan simulator calls task."""
    with unittest.mock.patch.object(simulator, "end_scan", wraps=simulator.end_scan) as end_scan:
        simulation_api.end_scan(task_callback)
        end_scan.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=37),
        call(progress=63),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_abort(
    simulation_api: PstSmrbProcessApiSimulator,
    simulator: PstSmrbSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that abort simulator calls task."""
    with unittest.mock.patch.object(simulator, "abort", wraps=simulator.abort) as abort:
        simulation_api.abort(task_callback)
        abort.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=59),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_smrb_grpc_sends_connect_request(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    client_id: str,
) -> None:
    """Test that SMRB gRPC API connects to the server."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    grpc_api.connect()

    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=client_id))


def test_smrb_grpc_assign_resources(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    assign_resources_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC assign resources."""
    response = AssignResourcesResponse()
    mock_servicer_context.assign_resources = MagicMock(return_value=response)
    resources = calculate_smrb_subband_resources(1, assign_resources_request)[1]

    grpc_api.assign_resources(resources, task_callback=task_callback)

    expected_smrb_request = SmrbResources(**resources)
    expected_request = AssignResourcesRequest(smrb=expected_smrb_request)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=True)


def test_smrb_grpc_assign_resources_when_already_assigned(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    assign_resources_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC assign resources when resources alreay assigned."""
    mock_servicer_context.assign_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.RESOURCES_ALREADY_ASSIGNED,
        message="Resources have already been assigned",
    )
    resources = calculate_smrb_subband_resources(1, assign_resources_request)[1]

    grpc_api.assign_resources(resources, task_callback=task_callback)

    expected_smrb_request = SmrbResources(**resources)
    expected_request = AssignResourcesRequest(smrb=expected_smrb_request)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Resources have already been assigned", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_assign_resources_when_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    assign_resources_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC assign resources throws an exception."""
    mock_servicer_context.assign_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    resources = calculate_smrb_subband_resources(1, assign_resources_request)[1]

    grpc_api.assign_resources(resources, task_callback=task_callback)

    expected_smrb_request = SmrbResources(**resources)
    expected_request = AssignResourcesRequest(smrb=expected_smrb_request)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_release_resources(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC release resources."""
    response = ReleaseResourcesResponse()
    mock_servicer_context.release_resources = MagicMock(return_value=response)

    grpc_api.release_resources(task_callback=task_callback)

    mock_servicer_context.release_resources.assert_called_once_with(ReleaseResourcesRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=False)


def test_smrb_grpc_release_resources_when_no_resources_assigned(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB release resources when there are not resources assigned."""
    mock_servicer_context.release_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.RESOURCES_NOT_ASSIGNED,
        message="No resources have been assigned",
    )

    grpc_api.release_resources(task_callback=task_callback)

    mock_servicer_context.release_resources.assert_called_once_with(ReleaseResourcesRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="No resources have been assigned"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=False)


def test_smrb_grpc_release_resources_when_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB release resources when an exception is thrown."""
    mock_servicer_context.release_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Oops there was a problem",
    )

    grpc_api.release_resources(task_callback=task_callback)

    mock_servicer_context.release_resources.assert_called_once_with(ReleaseResourcesRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Oops there was a problem", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_scan(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC scan."""
    response = ScanResponse()
    mock_servicer_context.scan = MagicMock(return_value=response)

    grpc_api.scan(args={}, task_callback=task_callback)

    mock_servicer_context.scan.assert_called_once_with(ScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=True)


def test_smrb_grpc_scan_when_already_scanning(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC scan when already scanning."""
    mock_servicer_context.scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.ALREADY_SCANNING,
        message="We are already scanning",
    )

    grpc_api.scan(args={}, task_callback=task_callback)

    mock_servicer_context.scan.assert_called_once_with(ScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=True)


def test_smrb_grpc_scan_when_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC scan when an exception is thrown."""
    mock_servicer_context.scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Oops there was a problem",
    )

    grpc_api.scan(args={}, task_callback=task_callback)

    mock_servicer_context.scan.assert_called_once_with(ScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Oops there was a problem", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_end_scan(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC end scan."""
    response = EndScanResponse()
    mock_servicer_context.end_scan = MagicMock(return_value=response)

    grpc_api.end_scan(task_callback=task_callback)

    mock_servicer_context.end_scan.assert_called_once_with(EndScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=False)


def test_smrb_grpc_end_scan_when_not_scanning(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC end scan when not scanning."""
    mock_servicer_context.end_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_SCANNING,
        message="We're not scanning. End Scan doesn't need to do anything",
    )

    grpc_api.end_scan(task_callback=task_callback)

    mock_servicer_context.end_scan.assert_called_once_with(EndScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=False)


def test_smrb_grpc_end_scan_when_exception_thrown(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC end scan when an exception is thrown."""
    mock_servicer_context.end_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Something is wrong!",
    )

    grpc_api.end_scan(task_callback=task_callback)

    mock_servicer_context.end_scan.assert_called_once_with(EndScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Something is wrong!", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_simulated_monitor_calls_callback(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""
    nbufs = randint(1, 100)
    data_stats_bufsz = randint(100, 200)
    weights_stats_bufsz = randint(10, 20)
    written = randint(2, 100)
    read = written - 1
    full = randint(0, nbufs)

    def response_generator() -> Generator[MonitorResponse, None, None]:
        while True:
            data = SmrbStatitics(
                nbufs=nbufs,
                bufsz=data_stats_bufsz,
                written=written,
                read=read,
                full=full,
                clear=nbufs - full,
                available=nbufs - full,
            )
            weights = SmrbStatitics(
                nbufs=nbufs,
                bufsz=weights_stats_bufsz,
                written=written,
                read=read,
                full=full,
                clear=nbufs - full,
                available=nbufs - full,
            )

            logger.debug("Yielding monitor data")
            yield MonitorResponse(smrb=SmrbMonitorData(data=data, weights=weights))
            time.sleep(0.5)

    mock_servicer_context.monitor = MagicMock()
    mock_servicer_context.monitor.return_value = response_generator()

    def _abort_monitor() -> None:
        logger.debug("Test sleeping 1s")
        time.sleep(1)
        logger.debug("Aborting monitoring.")
        abort_event.set()

    abort_thread = threading.Thread(target=_abort_monitor, daemon=True)
    abort_thread.start()

    grpc_api.monitor(
        subband_monitor_data_callback=subband_monitor_data_callback,
        polling_rate=500,
        monitor_abort_event=abort_event,
    )
    abort_thread.join()
    logger.debug("Abort thread finished.")

    buffer_size = data_stats_bufsz + weights_stats_bufsz
    total_written = buffer_size * written
    total_read = buffer_size * read
    calls = [
        call(
            subband_id=1,
            subband_data=SubbandMonitorData(
                buffer_size=buffer_size,
                total_written=total_written,
                total_read=total_read,
                full=full,
                num_of_buffers=nbufs,
            ),
        )
    ]
    subband_monitor_data_callback.assert_has_calls(calls=calls)
