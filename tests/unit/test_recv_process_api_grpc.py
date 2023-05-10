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
from random import randint, random
from typing import Any, Dict, Generator, List
from unittest.mock import ANY, MagicMock, call

import grpc
import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AbortRequest,
    AbortResponse,
    BeamConfiguration,
    ConfigureBeamRequest,
    ConfigureBeamResponse,
    ConfigureScanRequest,
    ConfigureScanResponse,
    ConnectionRequest,
    ConnectionResponse,
    DeconfigureBeamRequest,
    DeconfigureBeamResponse,
    DeconfigureScanRequest,
    DeconfigureScanResponse,
    ErrorCode,
    GetEnvironmentResponse,
    GoToFaultRequest,
    GoToFaultResponse,
    MonitorData,
    MonitorResponse,
    ReceiveBeamConfiguration,
    ReceiveMonitorData,
    ReceiveScanConfiguration,
    ReceiveSubbandResources,
    ResetRequest,
    ResetResponse,
    ScanConfiguration,
    StartScanRequest,
    StartScanResponse,
    StopScanRequest,
    StopScanResponse,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_process_api import (
    GIGABITS_PER_BYTE,
    PstReceiveProcessApi,
    PstReceiveProcessApiGrpc,
)
from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources, generate_recv_scan_request
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.validation import ValidationError


@pytest.fixture
def grpc_api(
    client_id: str,
    grpc_endpoint: str,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    background_task_processor: BackgroundTaskProcessor,
    mock_servicer_context: MagicMock,
) -> PstReceiveProcessApi:
    """Fixture to create instance of a gRPC API with client."""
    # ensure we reset the mock before the API is going to be called.
    mock_servicer_context.reset_mock()
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
    configure_beam_request: Dict[str, Any],
    recv_data_host: str,
    subband_udp_ports: List[int],
) -> dict:
    """Calculate RECV subband resources."""
    return calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
        data_host=recv_data_host,
        subband_udp_ports=subband_udp_ports,
    )


@pytest.fixture
def mapped_configure_request(
    configure_scan_request: Dict[str, Any],
) -> dict:
    """Map configure scan request to RECV properties."""
    return generate_recv_scan_request(request_params=configure_scan_request)


@pytest.fixture
def subband_configure_beam_request(
    subband_id: int,
    calculated_receive_subband_resources: dict,
) -> dict:
    """Create RECV subband request from calculated subband resources."""
    return {
        "common": calculated_receive_subband_resources["common"],
        "subband": calculated_receive_subband_resources["subbands"][subband_id],
    }


@pytest.fixture
def expected_beam_configuration_protobuf(
    subband_configure_beam_request: Dict[str, Any],
) -> ReceiveBeamConfiguration:
    """Create expected protobuf resources message for RECV."""
    return ReceiveBeamConfiguration(
        **subband_configure_beam_request["common"],
        subband_resources=ReceiveSubbandResources(
            **subband_configure_beam_request["subband"],
        ),
    )


@pytest.fixture
def expected_receive_configure_protobuf(
    mapped_configure_request: dict,
) -> ReceiveScanConfiguration:
    """Fixture to build expected RECV scan configuration request."""
    return ReceiveScanConfiguration(**mapped_configure_request)


def test_receive_grpc_validate_configure_beam(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    subband_configure_beam_request: Dict[str, Any],
    expected_beam_configuration_protobuf: ReceiveBeamConfiguration,
) -> None:
    """Test that RECV gRPC validate_configure_beam is called."""
    response = ConfigureBeamResponse()
    mock_servicer_context.configure_beam = MagicMock(return_value=response)

    grpc_api.validate_configure_beam(configuration=subband_configure_beam_request)

    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(receive=expected_beam_configuration_protobuf),
        dry_run=True,
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)


def test_receive_grpc_validate_configure_beam_throws_invalid_request(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    subband_configure_beam_request: Dict[str, Any],
    expected_beam_configuration_protobuf: ReceiveBeamConfiguration,
) -> None:
    """Test that RECV gRPC validate_configure_beam is called when there are validation errors."""
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INVALID_REQUEST,
        message="Validate configure beam error.",
    )

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_beam(configuration=subband_configure_beam_request)

    assert e_info.value.message == "Validate configure beam error."

    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(receive=expected_beam_configuration_protobuf),
        dry_run=True,
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)


def test_receive_grpc_validate_configure_beam_throws_resources_already_assigned(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    subband_configure_beam_request: Dict[str, Any],
    expected_beam_configuration_protobuf: ReceiveBeamConfiguration,
) -> None:
    """Test that RECV gRPC validate_configure_beam when already beam configured."""
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_BEAM_ALREADY,
        message="Beam configured already.",
    )

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_beam(configuration=subband_configure_beam_request)

    assert e_info.value.message == "Beam configured already."

    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(receive=expected_beam_configuration_protobuf),
        dry_run=True,
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)


def test_receive_grpc_configure_beam(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    subband_configure_beam_request: Dict[str, Any],
    expected_beam_configuration_protobuf: ReceiveBeamConfiguration,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC configure beam."""
    response = ConfigureBeamResponse()
    mock_servicer_context.configure_beam = MagicMock(return_value=response)

    grpc_api.configure_beam(subband_configure_beam_request, task_callback=task_callback)

    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(receive=expected_beam_configuration_protobuf)
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=True)


def test_receive_grpc_configure_beam_when_beam_configured(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    subband_configure_beam_request: Dict[str, Any],
    expected_beam_configuration_protobuf: ReceiveBeamConfiguration,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC configure beam when beam already configured."""
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_BEAM_ALREADY,
        message="Beam has already been configured",
    )

    grpc_api.configure_beam(subband_configure_beam_request, task_callback=task_callback)

    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(receive=expected_beam_configuration_protobuf)
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Beam has already been configured", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_receive_grpc_configure_beam_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    subband_configure_beam_request: Dict[str, Any],
    expected_beam_configuration_protobuf: ReceiveBeamConfiguration,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC configure beam throws an exception."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.configure_beam(subband_configure_beam_request, task_callback=task_callback)

    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(receive=expected_beam_configuration_protobuf)
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_receive_grpc_deconfigure_beam(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC deconfigure beam."""
    response = DeconfigureBeamResponse()
    mock_servicer_context.deconfigure_beam = MagicMock(return_value=response)

    grpc_api.deconfigure_beam(task_callback=task_callback)

    mock_servicer_context.deconfigure_beam.assert_called_once_with(DeconfigureBeamRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=False)


def test_receive_grpc_deconfigure_beam_when_no_resources_assigned(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV deconfigure beam when there are not beam configured."""
    mock_servicer_context.deconfigure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_CONFIGURED_FOR_BEAM,
        message="No resources have been assigned",
    )

    grpc_api.deconfigure_beam(task_callback=task_callback)

    mock_servicer_context.deconfigure_beam.assert_called_once_with(DeconfigureBeamRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="No resources have been assigned"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=False)


def test_receive_grpc_deconfigure_beam_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV deconfigure beam when an exception is thrown."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.deconfigure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Oops there was a problem",
    )

    grpc_api.deconfigure_beam(task_callback=task_callback)

    mock_servicer_context.deconfigure_beam.assert_called_once_with(DeconfigureBeamRequest())
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Oops there was a problem", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_validate_configure_scan(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    expected_receive_configure_protobuf: ReceiveScanConfiguration,
) -> None:
    """Test that DSP gRPC validate_configure_scan is called."""
    response = ConfigureScanResponse()
    mock_servicer_context.configure_scan = MagicMock(return_value=response)

    grpc_api.validate_configure_scan(configure_scan_request)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(receive=expected_receive_configure_protobuf),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_recv_grpc_validate_configure_scan_throws_invalid_request(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    expected_receive_configure_protobuf: ReceiveScanConfiguration,
) -> None:
    """Test that DSP gRPC validate_configure_beam is called when there are validation errors."""
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INVALID_REQUEST,
        message="Validate configure scan error.",
    )

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_scan(configuration=configure_scan_request)

    assert e_info.value.message == "Validate configure scan error."

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(receive=expected_receive_configure_protobuf),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_recv_grpc_validate_configure_scan_throws_scan_already_configured(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    expected_receive_configure_protobuf: ReceiveScanConfiguration,
) -> None:
    """Test that DSP gRPC validate_configure_scan is called when already configured for scanning."""
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_SCAN_ALREADY,
        message="Already configured for scanning.",
    )

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_scan(configuration=configure_scan_request)

    assert e_info.value.message == "Already configured for scanning."

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(receive=expected_receive_configure_protobuf),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_recv_grpc_configure_scan(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
    expected_receive_configure_protobuf: ReceiveScanConfiguration,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC calls configure_scan on remote service."""
    response = ConfigureScanResponse()
    mock_servicer_context.configure_scan = MagicMock(return_value=response)

    grpc_api.configure_scan(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(receive=expected_receive_configure_protobuf)
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=True)


def test_recv_grpc_configure_when_already_configured(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
    expected_receive_configure_protobuf: ReceiveScanConfiguration,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC configure scan and already configured."""
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_SCAN_ALREADY,
        message="Scan has already been configured.",
    )
    grpc_api.configure_scan(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(receive=expected_receive_configure_protobuf)
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Scan has already been configured.", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_recv_grpc_configure_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
    expected_receive_configure_protobuf: ReceiveScanConfiguration,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC configure beam throws an exception."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.configure_scan(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(receive=expected_receive_configure_protobuf)
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_deconfigure_scan(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC calls configure_scan on remote service."""
    response = DeconfigureScanResponse()
    mock_servicer_context.deconfigure_scan = MagicMock(return_value=response)

    grpc_api.deconfigure_scan(task_callback=task_callback)

    mock_servicer_context.deconfigure_scan.assert_called_once_with(DeconfigureScanRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False)


def test_recv_grpc_deconfigure_when_not_configured_for_scan(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC deconfigure scan and currently not configured."""
    mock_servicer_context.deconfigure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_CONFIGURED_FOR_SCAN,
        message="Not configured for scan.",
    )
    grpc_api.deconfigure_scan(task_callback=task_callback)

    mock_servicer_context.deconfigure_scan.assert_called_once_with(DeconfigureScanRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Not configured for scan."),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False)


def test_recv_grpc_deconfigure_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC deconfigure scan throws an exception."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.deconfigure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.deconfigure_scan(task_callback=task_callback)

    mock_servicer_context.deconfigure_scan.assert_called_once_with(DeconfigureScanRequest())
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_scan(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: Dict[str, Any],
    expected_scan_request_protobuf: StartScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC scan."""
    response = StartScanResponse()
    mock_servicer_context.start_scan = MagicMock(return_value=response)

    grpc_api.start_scan(args=scan_request, task_callback=task_callback)

    mock_servicer_context.start_scan.assert_called_once_with(expected_scan_request_protobuf)
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=True)


def test_recv_grpc_scan_when_already_scanning(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: Dict[str, Any],
    expected_scan_request_protobuf: StartScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC scan when already scanning."""
    mock_servicer_context.start_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.ALREADY_SCANNING,
        message="We are already scanning",
    )

    grpc_api.start_scan(args=scan_request, task_callback=task_callback)

    mock_servicer_context.start_scan.assert_called_once_with(expected_scan_request_protobuf)
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=True)


def test_recv_grpc_scan_when_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: Dict[str, Any],
    expected_scan_request_protobuf: StartScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC scan when an exception is thrown."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.start_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Oops there was a problem",
    )

    grpc_api.start_scan(args=scan_request, task_callback=task_callback)

    mock_servicer_context.start_scan.assert_called_once_with(expected_scan_request_protobuf)
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Oops there was a problem", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_stop_scan(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC end scan."""
    response = StopScanResponse()
    mock_servicer_context.stop_scan = MagicMock(return_value=response)

    grpc_api.stop_scan(task_callback=task_callback)

    mock_servicer_context.stop_scan.assert_called_once_with(StopScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=False)


def test_recv_grpc_stop_scan_when_not_scanning(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC end scan when not scanning."""
    mock_servicer_context.stop_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_SCANNING,
        message="We're not scanning. End Scan doesn't need to do anything",
    )

    grpc_api.stop_scan(task_callback=task_callback)

    mock_servicer_context.stop_scan.assert_called_once_with(StopScanRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(scanning=False)


def test_recv_grpc_stop_scan_when_exception_thrown(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC end scan when an exception is thrown."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.stop_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Something is wrong!",
    )

    grpc_api.stop_scan(task_callback=task_callback)

    mock_servicer_context.stop_scan.assert_called_once_with(StopScanRequest())
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Something is wrong!", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_handle_monitor_response(
    grpc_api: PstReceiveProcessApiGrpc,
    subband_monitor_data_callback: MagicMock,
) -> None:
    """Test the handling of monitor data."""
    import numpy as np

    receive_rate = float(
        np.float32(random() / GIGABITS_PER_BYTE)
    )  # hack so we use f32 precision use in protobuf
    receive_rate_gbs = receive_rate * GIGABITS_PER_BYTE  # python's default is f64
    data_received = randint(1, 100)
    data_drop_rate = random()
    data_dropped = randint(1, 100)
    misordered_packets = randint(1, 100)
    misordered_packet_rate = random()
    malformed_packets = randint(1, 100)
    malformed_packet_rate = random()
    misdirected_packets = randint(1, 100)
    misdirected_packet_rate = random()
    checksum_failure_packets = randint(1, 100)
    checksum_failure_packet_rate = random()
    timestamp_sync_error_packets = randint(1, 100)
    timestamp_sync_error_packet_rate = random()
    seq_number_sync_error_packets = randint(1, 100)
    seq_number_sync_error_packet_rate = random()

    receive_monitor_data = ReceiveMonitorData(
        receive_rate=receive_rate,
        data_received=data_received,
        data_drop_rate=data_drop_rate,
        data_dropped=data_dropped,
        misordered_packets=misordered_packets,
        misordered_packet_rate=misordered_packet_rate,
        malformed_packets=malformed_packets,
        malformed_packet_rate=malformed_packet_rate,
        misdirected_packets=misdirected_packets,
        misdirected_packet_rate=misdirected_packet_rate,
        checksum_failure_packets=checksum_failure_packets,
        checksum_failure_packet_rate=checksum_failure_packet_rate,
        timestamp_sync_error_packets=timestamp_sync_error_packets,
        timestamp_sync_error_packet_rate=timestamp_sync_error_packet_rate,
        seq_number_sync_error_packets=seq_number_sync_error_packets,
        seq_number_sync_error_packet_rate=seq_number_sync_error_packet_rate,
    )

    response_message = MonitorResponse(monitor_data=MonitorData(receive=receive_monitor_data))

    grpc_api._handle_monitor_response(response_message.monitor_data, subband_monitor_data_callback)

    subband_monitor_data_callback.assert_called_once_with(
        subband_id=1,
        subband_data=ReceiveData(
            # grab from the protobuf message given there can be rounding issues.
            data_received=receive_monitor_data.data_received,
            data_receive_rate=receive_rate_gbs,
            data_dropped=receive_monitor_data.data_dropped,
            data_drop_rate=receive_monitor_data.data_drop_rate,
            misordered_packets=receive_monitor_data.misordered_packets,
            misordered_packet_rate=receive_monitor_data.misordered_packet_rate,
            malformed_packets=receive_monitor_data.malformed_packets,
            malformed_packet_rate=receive_monitor_data.malformed_packet_rate,
            misdirected_packets=receive_monitor_data.misdirected_packets,
            misdirected_packet_rate=receive_monitor_data.misdirected_packet_rate,
            checksum_failure_packets=receive_monitor_data.checksum_failure_packets,
            checksum_failure_packet_rate=receive_monitor_data.checksum_failure_packet_rate,
            timestamp_sync_error_packets=receive_monitor_data.timestamp_sync_error_packets,
            timestamp_sync_error_packet_rate=receive_monitor_data.timestamp_sync_error_packet_rate,
            seq_number_sync_error_packets=receive_monitor_data.seq_number_sync_error_packets,
            seq_number_sync_error_packet_rate=receive_monitor_data.seq_number_sync_error_packet_rate,
        ),
    )


def test_recv_grpc_simulated_monitor_calls_callback(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""
    import numpy as np

    receive_rate = float(
        np.float32(random() / GIGABITS_PER_BYTE)
    )  # hack so we use f32 precision use in protobuf
    receive_rate_gbs = receive_rate * GIGABITS_PER_BYTE  # python's default is f64
    data_received = randint(1, 100)
    data_drop_rate = random()
    data_dropped = randint(1, 100)
    misordered_packets = randint(1, 100)

    monitior_data = ReceiveMonitorData(
        receive_rate=receive_rate,
        data_received=data_received,
        data_drop_rate=data_drop_rate,
        data_dropped=data_dropped,
        misordered_packets=misordered_packets,
    )

    def response_generator() -> Generator[MonitorResponse, None, None]:
        while True:
            logger.debug("Yielding monitor data")
            yield MonitorResponse(monitor_data=MonitorData(receive=monitior_data))
            time.sleep(0.05)

    mock_servicer_context.monitor = MagicMock()
    mock_servicer_context.monitor.return_value = response_generator()

    def _abort_monitor() -> None:
        logger.debug("Test sleeping 1s")
        time.sleep(0.1)
        logger.debug("Aborting monitoring.")
        abort_event.set()

    abort_thread = threading.Thread(target=_abort_monitor, daemon=True)
    abort_thread.start()

    grpc_api.monitor(
        subband_monitor_data_callback=subband_monitor_data_callback,
        polling_rate=10,
        monitor_abort_event=abort_event,
    )
    abort_thread.join()
    logger.debug("Abort thread finished.")

    calls = [
        call(
            subband_id=1,
            subband_data=ReceiveData(
                data_received=monitior_data.data_received,
                data_receive_rate=receive_rate_gbs,  # we get B/s not Gb/s,
                data_dropped=monitior_data.data_dropped,
                data_drop_rate=monitior_data.data_drop_rate,
                misordered_packets=monitior_data.misordered_packets,
            ),
        )
    ]
    subband_monitor_data_callback.assert_has_calls(calls=calls)


def test_recv_grpc_abort(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC abort."""
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


def test_recv_grpc_abort_throws_exception(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC abort when an exception is thrown."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.abort.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="We have an issue!",
    )

    grpc_api.abort(task_callback=task_callback)

    mock_servicer_context.abort.assert_called_once_with(AbortRequest())
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="We have an issue!", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_reset(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC reset."""
    response = ResetResponse()
    mock_servicer_context.reset = MagicMock(return_value=response)

    grpc_api.reset(task_callback=task_callback)

    mock_servicer_context.reset.assert_called_once_with(ResetRequest())
    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=False, resourced=False)


def test_recv_grpc_reset_when_exception_thrown(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that RECV gRPC reset when exception is thrown."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.reset.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Resetting error!",
    )

    grpc_api.reset(task_callback=task_callback)

    mock_servicer_context.reset.assert_called_once_with(ResetRequest())
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Resetting error!", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_go_to_fault(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
) -> None:
    """Test that RECV gRPC go_to_fault."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())

    grpc_api.go_to_fault()

    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_grpc_get_env(
    grpc_api: PstReceiveProcessApiGrpc,
    mock_servicer_context: MagicMock,
) -> None:
    """Test get_env via gRPC."""
    response = GetEnvironmentResponse()
    response.values["data_host"].string_value = "10.10.0.5"
    response.values["data_port"].signed_int_value = 32080
    mock_servicer_context.get_env = MagicMock(return_value=response)

    client_response = grpc_api.get_env()
    expected_response = {
        "data_host": "10.10.0.5",
        "data_port": 32080,
    }

    assert expected_response == client_response
