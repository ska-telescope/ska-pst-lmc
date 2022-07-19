# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV API."""

from __future__ import annotations

import logging
import time
import unittest
from typing import Callable
from unittest.mock import MagicMock, call

import grpc
import pytest
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.smrb.smrb_model import SharedMemoryRingBufferData
from ska_pst_lmc.smrb.smrb_process_api import PstSmrbProcessApiGrpc, PstSmrbProcessApiSimulator
from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AssignResourcesRequest,
    AssignResourcesResponse,
    ConnectionRequest,
    ConnectionResponse,
    ErrorCode,
    ReleaseResourcesRequest,
    ReleaseResourcesResponse,
    SmrbResources,
)


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
def simulator() -> PstSmrbSimulator:
    """Create instance of a simulator to be used within the API."""
    return PstSmrbSimulator()


def test_communication_task_on_connect_disconnect(simulation_api: PstSmrbProcessApiSimulator) -> None:
    """Assert start communicating starts a background task."""
    assert simulation_api._communication_task is None

    simulation_api.connect()

    assert simulation_api._communication_task is not None
    assert simulation_api._communication_task.running()

    simulation_api.disconnect()
    assert simulation_api._communication_task is None


def test_start_communicating_call_monitor(simulation_api: PstSmrbProcessApiSimulator) -> None:
    """Assert the background task used is the monitor method."""
    simulation_api._monitor_action = MagicMock(name="_monitor_task")  # type: ignore

    simulation_api._monitor_action.assert_not_called()

    simulation_api.connect()
    time.sleep(0.01)
    simulation_api._monitor_action.assert_called()


def test_monitor_function_gets_values_from_simulator(
    simulation_api: PstSmrbProcessApiSimulator, simulator: PstSmrbSimulator
) -> None:
    """Assert that the API values get data from simulator when monitor action called."""
    with unittest.mock.patch.object(simulator, "get_data", wraps=simulator.get_data) as get_data:
        simulation_api._monitor_action()
        get_data.assert_called_once()


def test_get_data_returns_empty_data_if_not_monitoring(simulation_api: PstSmrbProcessApiSimulator) -> None:
    """Test that the data returned when API is not scanning is the default data."""
    assert simulation_api.data is None

    actual: SharedMemoryRingBufferData = simulation_api.monitor_data
    assert actual is not None

    expected: SharedMemoryRingBufferData = SharedMemoryRingBufferData.defaults()

    assert actual == expected


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
    mock_servicer_context: MagicMock,
    grpc_port: int,
    client_id: str,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
) -> None:
    """Test that SMRB gRPC API connects to the server."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    api = PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logging.getLogger(__name__),
        component_state_callback=component_state_callback,
    )

    api.connect()

    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=client_id))


def test_smrb_grpc_assign_resources(
    mock_servicer_context: MagicMock,
    grpc_port: int,
    client_id: str,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    assign_resources_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC API connects to the server."""
    response = AssignResourcesResponse()
    mock_servicer_context.assign_resources = MagicMock(return_value=response)
    resources = calculate_smrb_subband_resources(1, assign_resources_request)[1]

    api = PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logging.getLogger(__name__),
        component_state_callback=component_state_callback,
    )

    api.assign_resources(resources, task_callback=task_callback)

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
    mock_servicer_context: MagicMock,
    grpc_port: int,
    client_id: str,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    assign_resources_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC API connects to the server."""
    mock_servicer_context.assign_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.RESOURCES_ALREADY_ASSIGNED,
        message="Resources have already been assigned",
    )
    resources = calculate_smrb_subband_resources(1, assign_resources_request)[1]

    api = PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logging.getLogger(__name__),
        component_state_callback=component_state_callback,
    )

    api.assign_resources(resources, task_callback=task_callback)

    expected_smrb_request = SmrbResources(**resources)
    expected_request = AssignResourcesRequest(smrb=expected_smrb_request)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Resources have already been assigned"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_release_resources(
    mock_servicer_context: MagicMock,
    grpc_port: int,
    client_id: str,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC API connects to the server."""
    response = ReleaseResourcesResponse()
    mock_servicer_context.release_resources = MagicMock(return_value=response)

    api = PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logging.getLogger(__name__),
        component_state_callback=component_state_callback,
    )

    api.release_resources(task_callback=task_callback)

    mock_servicer_context.release_resources.assert_called_once_with(ReleaseResourcesRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=False)


def test_smrb_grpc_release_resources_when_no_resources_assigned(
    mock_servicer_context: MagicMock,
    grpc_port: int,
    client_id: str,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC API connects to the server."""
    mock_servicer_context.release_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.RESOURCES_NOT_ASSIGNED,
        message="No resources have been assigned",
    )

    api = PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logging.getLogger(__name__),
        component_state_callback=component_state_callback,
    )

    api.release_resources(task_callback=task_callback)

    mock_servicer_context.release_resources.assert_called_once_with(ReleaseResourcesRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="No resources have been assigned"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=False)
