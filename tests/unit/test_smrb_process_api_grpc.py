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
from random import randint
from typing import Generator
from unittest.mock import ANY, MagicMock, call

import grpc
import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AbortRequest,
    AbortResponse,
    AssignResourcesRequest,
    AssignResourcesResponse,
    ConfigureRequest,
    ConfigureResponse,
    ConnectionRequest,
    ConnectionResponse,
    DeconfigureRequest,
    DeconfigureResponse,
    EndScanRequest,
    EndScanResponse,
    ErrorCode,
    GoToFaultRequest,
    GoToFaultResponse,
    MonitorData,
    MonitorResponse,
    ReleaseResourcesRequest,
    ReleaseResourcesResponse,
    ResetRequest,
    ResetResponse,
    ResourceConfiguration,
    RestartRequest,
    RestartResponse,
    ScanConfiguration,
    ScanRequest,
    ScanResponse,
    SmrbMonitorData,
    SmrbResources,
    SmrbScanConfiguration,
    SmrbStatitics,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.smrb.smrb_model import SubbandMonitorData
from ska_pst_lmc.smrb.smrb_process_api import PstSmrbProcessApiGrpc
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


@pytest.fixture
def grpc_api(
    client_id: str,
    grpc_port: int,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    background_task_processor: BackgroundTaskProcessor,
) -> PstSmrbProcessApiGrpc:
    """Fixture to create instance of a gRPC API with client."""
    return PstSmrbProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logger,
        component_state_callback=component_state_callback,
        background_task_processor=background_task_processor,
    )


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
    expected_request = AssignResourcesRequest(
        resource_configuration=ResourceConfiguration(smrb=expected_smrb_request)
    )
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
    expected_request = AssignResourcesRequest(
        resource_configuration=ResourceConfiguration(smrb=expected_smrb_request)
    )
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
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.assign_resources.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    resources = calculate_smrb_subband_resources(1, assign_resources_request)[1]

    grpc_api.assign_resources(resources, task_callback=task_callback)

    expected_smrb_request = SmrbResources(**resources)
    expected_request = AssignResourcesRequest(
        resource_configuration=ResourceConfiguration(smrb=expected_smrb_request)
    )
    mock_servicer_context.assign_resources.assert_called_once_with(expected_request)
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


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


def test_smrb_grpc_configure(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC calls configure on remote service."""
    response = ConfigureResponse()
    mock_servicer_context.configure = MagicMock(return_value=response)

    grpc_api.configure(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureRequest(scan_configuration=ScanConfiguration(smrb=SmrbScanConfiguration()))
    mock_servicer_context.configure.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=True)


def test_smrb_grpc_configure_when_already_configured(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC configure and already configured."""
    mock_servicer_context.configure.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.SCAN_CONFIGURED_ALREADY,
        message="Scan has already been configured.",
    )
    grpc_api.configure(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureRequest(scan_configuration=ScanConfiguration(smrb=SmrbScanConfiguration()))
    mock_servicer_context.configure.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Scan has already been configured.", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_configure_when_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: dict,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC assign resources throws an exception."""
    mock_servicer_context.configure.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.configure(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureRequest(scan_configuration=ScanConfiguration(smrb=SmrbScanConfiguration()))
    mock_servicer_context.configure.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_deconfigure(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC calls configure on remote service."""
    response = DeconfigureResponse()
    mock_servicer_context.deconfigure = MagicMock(return_value=response)

    grpc_api.deconfigure(task_callback=task_callback)

    mock_servicer_context.deconfigure.assert_called_once_with(DeconfigureRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False)


def test_smrb_grpc_deconfigure_when_not_configured_for_scan(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC deconfigure and currently not configured."""
    mock_servicer_context.deconfigure.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_CONFIGURED_FOR_SCAN,
        message="Not configured for scan.",
    )
    grpc_api.deconfigure(task_callback=task_callback)

    mock_servicer_context.deconfigure.assert_called_once_with(DeconfigureRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Not configured for scan."),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False)


def test_smrb_grpc_deconfigure_when_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC deconfigure throws an exception."""
    mock_servicer_context.deconfigure.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.deconfigure(task_callback=task_callback)

    mock_servicer_context.deconfigure.assert_called_once_with(DeconfigureRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_scan(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: dict,
    expected_scan_request_protobuf: ScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC scan."""
    response = ScanResponse()
    mock_servicer_context.scan = MagicMock(return_value=response)

    grpc_api.scan(args=scan_request, task_callback=task_callback)

    mock_servicer_context.scan.assert_called_once_with(expected_scan_request_protobuf)
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=True)


def test_smrb_grpc_scan_when_already_scanning(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: dict,
    expected_scan_request_protobuf: ScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC scan when already scanning."""
    mock_servicer_context.scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.ALREADY_SCANNING,
        message="We are already scanning",
    )

    grpc_api.scan(args=scan_request, task_callback=task_callback)

    mock_servicer_context.scan.assert_called_once_with(expected_scan_request_protobuf)
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=True)


def test_smrb_grpc_scan_when_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: dict,
    expected_scan_request_protobuf: ScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC scan when an exception is thrown."""
    mock_servicer_context.scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Oops there was a problem",
    )

    grpc_api.scan(args=scan_request, task_callback=task_callback)

    mock_servicer_context.scan.assert_called_once_with(expected_scan_request_protobuf)
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


def test_smrb_grpc_abort(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC abort."""
    response = AbortResponse()
    mock_servicer_context.abort = MagicMock(return_value=response)

    grpc_api.abort(task_callback=task_callback)

    mock_servicer_context.abort.assert_called_once_with(AbortRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=False)


def test_smrb_grpc_abort_throws_exception(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC abort when an exception is thrown."""
    mock_servicer_context.abort.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="We have an issue!",
    )

    grpc_api.abort(task_callback=task_callback)

    mock_servicer_context.abort.assert_called_once_with(AbortRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="We have an issue!", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_reset(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC reset."""
    response = ResetResponse()
    mock_servicer_context.reset = MagicMock(return_value=response)

    grpc_api.reset(task_callback=task_callback)

    mock_servicer_context.reset.assert_called_once_with(ResetRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False)


def test_smrb_grpc_reset_when_exception_thrown(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC reset when exception is thrown."""
    mock_servicer_context.reset.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Resetting error!",
    )

    grpc_api.reset(task_callback=task_callback)

    mock_servicer_context.reset.assert_called_once_with(ResetRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Resetting error!", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_smrb_grpc_restart(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC abort."""
    response = RestartResponse()
    mock_servicer_context.restart = MagicMock(return_value=response)

    grpc_api.restart(task_callback=task_callback)

    mock_servicer_context.restart.assert_called_once_with(RestartRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False, resourced=False)


def test_smrb_grpc_restart_when_exception_thrown(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC reset when exception is thrown."""
    mock_servicer_context.restart.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Resetting error!",
    )

    grpc_api.restart(task_callback=task_callback)

    mock_servicer_context.restart.assert_called_once_with(RestartRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Resetting error!", exception=ANY),
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
            yield MonitorResponse(monitor_data=MonitorData(smrb=SmrbMonitorData(data=data, weights=weights)))
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


def test_smrb_grpc_go_to_fault(
    grpc_api: PstSmrbProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
) -> None:
    """Test that SMRB gRPC go_to_fault."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())

    grpc_api.go_to_fault()

    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())
    component_state_callback.assert_called_once_with(obsfault=True)
