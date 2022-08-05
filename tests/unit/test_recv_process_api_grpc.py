# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV API."""

from __future__ import annotations

import logging
from unittest.mock import ANY, MagicMock, call

import grpc
import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AssignResourcesRequest,
    AssignResourcesResponse,
    ConnectionRequest,
    ConnectionResponse,
    ErrorCode,
    ReceiveResources,
    ReceiveSubbandResources,
    ReleaseResourcesRequest,
    ReleaseResourcesResponse,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.receive.receive_process_api import PstReceiveProcessApi, PstReceiveProcessApiGrpc
from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


@pytest.fixture
def grpc_api(
    client_id: str,
    grpc_endpoint: str,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    background_task_processor: BackgroundTaskProcessor,
) -> PstReceiveProcessApi:
    """Fixture to create instance of a gRPC API with client."""
    return PstReceiveProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=grpc_endpoint,
        logger=logger,
        component_state_callback=component_state_callback,
        background_task_processor=background_task_processor,
    )


def test_receive_grpc_sends_connect_request(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    client_id: str,
) -> None:
    """Test that RECV gRPC API connects to the server."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    grpc_api.connect()

    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=client_id))


@pytest.fixture
def subband_id() -> int:
    """Create subband."""
    return 1


@pytest.fixture
def calculated_receive_subband_resources(
    beam_id: int,
    assign_resources_request: dict,
) -> dict:
    """Calculate RECV subband resources."""
    return calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
    )


@pytest.fixture
def subband_assign_resources_request(
    subband_id: int,
    calculated_receive_subband_resources: dict,
) -> dict:
    """Create RECV subband request from calculated subband resources."""
    return {
        "common": calculated_receive_subband_resources["common"],
        "subband": calculated_receive_subband_resources["subbands"][subband_id],
    }


@pytest.fixture
def expected_receive_resources_protobuf(
    subband_assign_resources_request: dict,
) -> ReceiveResources:
    """Create expected protobuf resources message for RECV."""
    return ReceiveResources(
        **subband_assign_resources_request["common"],
        subband_resources=ReceiveSubbandResources(
            **subband_assign_resources_request["subband"],
        ),
    )


def test_receive_grpc_assign_resources(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    subband_assign_resources_request: dict,
    expected_receive_resources_protobuf: dict,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC assign resources."""
    response = AssignResourcesResponse()
    mock_servicer_context.assign_resources = MagicMock(return_value=response)

    grpc_api.assign_resources(subband_assign_resources_request, task_callback=task_callback)

    expected_request = AssignResourcesRequest(receive=expected_receive_resources_protobuf)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=True)


def test_receive_grpc_assign_resources_when_already_assigned(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    subband_assign_resources_request: dict,
    expected_receive_resources_protobuf: dict,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC assign resources when resources alreay assigned."""
    mock_servicer_context.assign_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.RESOURCES_ALREADY_ASSIGNED,
        message="Resources have already been assigned",
    )

    grpc_api.assign_resources(subband_assign_resources_request, task_callback=task_callback)

    expected_request = AssignResourcesRequest(receive=expected_receive_resources_protobuf)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Resources have already been assigned", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_receive_grpc_assign_resources_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    subband_assign_resources_request: dict,
    expected_receive_resources_protobuf: dict,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC assign resources throws an exception."""
    mock_servicer_context.assign_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.assign_resources(subband_assign_resources_request, task_callback=task_callback)

    expected_request = AssignResourcesRequest(receive=expected_receive_resources_protobuf)
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_receive_grpc_release_resources(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC release resources."""
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


def test_receive_grpc_release_resources_when_no_resources_assigned(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV release resources when there are not resources assigned."""
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


def test_receive_grpc_release_resources_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV release resources when an exception is thrown."""
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
