# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains tests for the STAT API."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Generator
from unittest.mock import ANY, MagicMock, call

import grpc
import numpy as np
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
    GoToFaultRequest,
    GoToFaultResponse,
    LogLevel,
    MonitorData,
    MonitorResponse,
    ResetRequest,
    ResetResponse,
    ScanConfiguration,
    SetLogLevelRequest,
    SetLogLevelResponse,
    StartScanRequest,
    StartScanResponse,
    StatBeamConfiguration,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import StatMonitorData as StatMonitorDataProto
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import StatScanConfiguration, StopScanRequest, StopScanResponse
from ska_tango_base.commands import TaskStatus
from ska_tango_base.control_model import LoggingLevel

from ska_pst_lmc.stat import (
    DEFAULT_NUM_REBIN,
    DEFAULT_PROCESSING_DELAY_MS,
    DEFAULT_REQ_FREQ_BINS,
    DEFAULT_REQ_TIME_BINS,
)
from ska_pst_lmc.stat.stat_model import StatMonitorData
from ska_pst_lmc.stat.stat_process_api import IMAG_IDX, POLA_IDX, POLB_IDX, REAL_IDX, PstStatProcessApiGrpc
from ska_pst_lmc.stat.stat_util import calculate_stat_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.validation import ValidationError


@pytest.fixture
def grpc_api(
    client_id: str,
    grpc_port: int,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    background_task_processor: BackgroundTaskProcessor,
    mock_servicer_context: MagicMock,
) -> PstStatProcessApiGrpc:
    """Fixture to create instance of a gRPC API with client."""
    # ensure we reset the mock before the API is going to be called.
    mock_servicer_context.reset_mock()
    return PstStatProcessApiGrpc(
        client_id=client_id,
        grpc_endpoint=f"127.0.0.1:{grpc_port}",
        logger=logger,
        component_state_callback=component_state_callback,
        background_task_processor=background_task_processor,
    )


def test_stat_grpc_sends_connect_request(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    client_id: str,
) -> None:
    """Test that  API connects to the server."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    grpc_api.connect()

    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=client_id))


def test_stat_grpc_validate_configure_beam(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_beam_request: Dict[str, Any],
) -> None:
    """Test that  validate_configure_beam is called."""
    response = ConfigureBeamResponse()
    mock_servicer_context.configure_beam = MagicMock(return_value=response)
    configuration = calculate_stat_subband_resources(beam_id=1)[1]

    grpc_api.validate_configure_beam(configuration=configuration)

    expected_stat_request = StatBeamConfiguration(**configuration)
    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(stat=expected_stat_request),
        dry_run=True,
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)


def test_stat_grpc_validate_configure_beam_throws_invalid_request(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_beam_request: Dict[str, Any],
) -> None:
    """Test that validate_configure_beam throws exception when there are validation errors."""
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INVALID_REQUEST,
        message="Validate configure beam error.",
    )

    configuration = calculate_stat_subband_resources(beam_id=1)[1]

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_beam(configuration=configuration)

    assert e_info.value.message == "Validate configure beam error."

    expected_stat_request = StatBeamConfiguration(**configuration)
    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(stat=expected_stat_request),
        dry_run=True,
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)


def test_stat_grpc_validate_configure_beam_throws_resources_already_assigned(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_beam_request: Dict[str, Any],
) -> None:
    """Test that  validate_configure_beam throws exception when already beam configured."""
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_BEAM_ALREADY,
        message="Beam configured already.",
    )

    configuration = calculate_stat_subband_resources(beam_id=1)[1]

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_beam(configuration=configuration)

    assert e_info.value.message == "Beam configured already."

    expected_stat_request = StatBeamConfiguration(**configuration)
    expected_request = ConfigureBeamRequest(
        beam_configuration=BeamConfiguration(stat=expected_stat_request),
        dry_run=True,
    )
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)


def test_stat_grpc_configure_beam(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_beam_request: Dict[str, Any],
    task_callback: MagicMock,
) -> None:
    """Test that  configure beam."""
    response = ConfigureBeamResponse()
    mock_servicer_context.configure_beam = MagicMock(return_value=response)
    resources = calculate_stat_subband_resources(beam_id=1)[1]

    grpc_api.configure_beam(resources, task_callback=task_callback)

    expected_stat_request = StatBeamConfiguration(**resources)
    expected_request = ConfigureBeamRequest(beam_configuration=BeamConfiguration(stat=expected_stat_request))
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(resourced=True)


def test_stat_grpc_configure_beam_when_beam_configured(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_beam_request: Dict[str, Any],
    task_callback: MagicMock,
) -> None:
    """Test that  configure beam when beam already configured."""
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_BEAM_ALREADY,
        message="Beam has already been configured",
    )
    resources = calculate_stat_subband_resources(beam_id=1)[1]

    grpc_api.configure_beam(resources, task_callback=task_callback)

    expected_stat_request = StatBeamConfiguration(**resources)
    expected_request = ConfigureBeamRequest(beam_configuration=BeamConfiguration(stat=expected_stat_request))
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Beam has already been configured", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_stat_grpc_configure_beam_when_throws_exception(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_beam_request: Dict[str, Any],
    task_callback: MagicMock,
) -> None:
    """Test that  configure beam throws an exception."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.configure_beam.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    resources = calculate_stat_subband_resources(beam_id=1)[1]

    grpc_api.configure_beam(resources, task_callback=task_callback)

    expected_stat_request = StatBeamConfiguration(**resources)
    expected_request = ConfigureBeamRequest(beam_configuration=BeamConfiguration(stat=expected_stat_request))
    mock_servicer_context.configure_beam.assert_called_once_with(expected_request)
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_stat_grpc_deconfigure_beam(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  deconfigure beam."""
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


def test_stat_grpc_deconfigure_beam_when_no_resources_assigned(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that STAT deconfigure beam when there are not beam configured."""
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


def test_stat_grpc_deconfigure_beam_when_throws_exception(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that STAT deconfigure beam when an exception is thrown."""
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


def test_stat_grpc_validate_configure_scan_with_defaults(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    eb_id: str,
) -> None:
    """Test that  validate_configure_scan is called with default parameters."""
    response = ConfigureScanResponse()
    mock_servicer_context.configure_scan = MagicMock(return_value=response)

    grpc_api.validate_configure_scan(configure_scan_request)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=DEFAULT_PROCESSING_DELAY_MS,
                req_time_bins=DEFAULT_REQ_TIME_BINS,
                req_freq_bins=DEFAULT_REQ_FREQ_BINS,
                num_rebin=DEFAULT_NUM_REBIN,
            )
        ),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_stat_grpc_validate_configure_scan_with_overriden_values(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    eb_id: str,
) -> None:
    """Test that  validate_configure_scan is called with overriden parameters."""
    response = ConfigureScanResponse()
    mock_servicer_context.configure_scan = MagicMock(return_value=response)

    configure_scan_request["stat_processing_delay_ms"] = np.random.randint(low=10, high=2000)
    configure_scan_request["stat_req_time_bins"] = np.random.randint(low=10, high=2000)
    configure_scan_request["stat_req_freq_bins"] = np.random.randint(low=10, high=2000)
    configure_scan_request["stat_num_rebin"] = np.random.randint(low=10, high=2000)

    grpc_api.validate_configure_scan(configure_scan_request)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=configure_scan_request["stat_processing_delay_ms"],
                req_time_bins=configure_scan_request["stat_req_time_bins"],
                req_freq_bins=configure_scan_request["stat_req_freq_bins"],
                num_rebin=configure_scan_request["stat_num_rebin"],
            )
        ),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_stat_grpc_validate_configure_scan_throws_invalid_request(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    eb_id: str,
) -> None:
    """Test that validate_configure_scan throws exception when there are validation errors."""
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INVALID_REQUEST,
        message="Validate configure scan error.",
    )

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_scan(configuration=configure_scan_request)

    assert e_info.value.message == "Validate configure scan error."

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=DEFAULT_PROCESSING_DELAY_MS,
                req_time_bins=DEFAULT_REQ_TIME_BINS,
                req_freq_bins=DEFAULT_REQ_FREQ_BINS,
                num_rebin=DEFAULT_NUM_REBIN,
            )
        ),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_stat_grpc_validate_configure_scan_throws_scan_already_configured(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    configure_scan_request: Dict[str, Any],
    eb_id: str,
) -> None:
    """Test that validate_configure_scan throws exception when already configured for scanning."""
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_SCAN_ALREADY,
        message="Already configured for scanning.",
    )

    with pytest.raises(ValidationError) as e_info:
        grpc_api.validate_configure_scan(configuration=configure_scan_request)

    assert e_info.value.message == "Already configured for scanning."

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=DEFAULT_PROCESSING_DELAY_MS,
                req_time_bins=DEFAULT_REQ_TIME_BINS,
                req_freq_bins=DEFAULT_REQ_FREQ_BINS,
                num_rebin=DEFAULT_NUM_REBIN,
            )
        ),
        dry_run=True,
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)


def test_stat_grpc_configure_scan(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
    task_callback: MagicMock,
    eb_id: str,
) -> None:
    """Test that  calls configure_scan on remote service."""
    response = ConfigureScanResponse()
    mock_servicer_context.configure_scan = MagicMock(return_value=response)

    grpc_api.configure_scan(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=DEFAULT_PROCESSING_DELAY_MS,
                req_time_bins=DEFAULT_REQ_TIME_BINS,
                req_freq_bins=DEFAULT_REQ_FREQ_BINS,
                num_rebin=DEFAULT_NUM_REBIN,
            )
        )
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(configured=True)


def test_stat_grpc_configure_when_already_configured(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
    task_callback: MagicMock,
    eb_id: str,
) -> None:
    """Test that  configure scan and already configured."""
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.CONFIGURED_FOR_SCAN_ALREADY,
        message="Scan has already been configured.",
    )
    grpc_api.configure_scan(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=DEFAULT_PROCESSING_DELAY_MS,
                req_time_bins=DEFAULT_REQ_TIME_BINS,
                req_freq_bins=DEFAULT_REQ_FREQ_BINS,
                num_rebin=DEFAULT_NUM_REBIN,
            )
        )
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Scan has already been configured.", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_not_called()


def test_stat_grpc_configure_when_throws_exception(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
    task_callback: MagicMock,
    eb_id: str,
) -> None:
    """Test that  configure scan throws an exception."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())
    mock_servicer_context.configure_scan.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error occurred",
    )
    grpc_api.configure_scan(configure_scan_request, task_callback=task_callback)

    expected_request = ConfigureScanRequest(
        scan_configuration=ScanConfiguration(
            stat=StatScanConfiguration(
                execution_block_id=eb_id,
                processing_delay_ms=DEFAULT_PROCESSING_DELAY_MS,
                req_time_bins=DEFAULT_REQ_TIME_BINS,
                req_freq_bins=DEFAULT_REQ_FREQ_BINS,
                num_rebin=DEFAULT_NUM_REBIN,
            )
        )
    )
    mock_servicer_context.configure_scan.assert_called_once_with(expected_request)
    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, result="Internal server error occurred", exception=ANY),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_once_with(obsfault=True)


def test_stat_grpc_deconfigure_scan(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  calls deconfigure_scan on remote service."""
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


def test_stat_grpc_deconfigure_when_not_configured_for_scan(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  deconfigure scan and currently not configured."""
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


def test_stat_grpc_deconfigure_when_throws_exception(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  deconfigure scan throws an exception."""
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


def test_stat_grpc_scan(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: Dict[str, Any],
    expected_scan_request_protobuf: StartScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  scan."""
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


def test_stat_grpc_scan_when_already_scanning(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: Dict[str, Any],
    expected_scan_request_protobuf: StartScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  scan when already scanning."""
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


def test_stat_grpc_scan_when_throws_exception(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    scan_request: Dict[str, Any],
    expected_scan_request_protobuf: StartScanRequest,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  scan when an exception is thrown."""
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


def test_stat_grpc_stop_scan(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  end scan."""
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


def test_stat_grpc_stop_scan_when_not_scanning(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  end scan when not scanning."""
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


def test_stat_grpc_stop_scan_when_exception_thrown(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  end scan when an exception is thrown."""
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


def test_stat_grpc_abort(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  abort."""
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


def test_stat_grpc_abort_throws_exception(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  abort when an exception is thrown."""
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


def test_stat_grpc_reset(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  reset."""
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


def test_stat_grpc_reset_when_exception_thrown(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that  reset when exception is thrown."""
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


def test_stat_grpc_simulated_monitor_calls_callback(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""
    mean_frequency_avg = np.random.rand(4).astype(np.float32)
    mean_frequency_avg_rfi_excised = np.random.rand(4).astype(np.float32)
    variance_frequency_avg = np.random.rand(4).astype(np.float32)
    variance_frequency_avg_rfi_excised = np.random.rand(4).astype(np.float32)
    num_clipped_samples = np.random.randint(128, size=(4,))
    num_clipped_samples_rfi_excised = np.random.randint(128, size=(4,))

    def response_generator() -> Generator[MonitorResponse, None, None]:
        while True:
            logger.debug("Yielding monitor data")
            yield MonitorResponse(
                monitor_data=MonitorData(
                    stat=StatMonitorDataProto(
                        mean_frequency_avg=mean_frequency_avg,
                        mean_frequency_avg_masked=mean_frequency_avg_rfi_excised,
                        variance_frequency_avg=variance_frequency_avg,
                        variance_frequency_avg_masked=variance_frequency_avg_rfi_excised,
                        num_clipped_samples=num_clipped_samples,
                        num_clipped_samples_masked=num_clipped_samples_rfi_excised,
                    )
                )
            )
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
        polling_rate=50,
        monitor_abort_event=abort_event,
    )
    abort_thread.join()
    logger.debug("Abort thread finished.")

    def _idx(pol_idx: int, dim_idx: int) -> int:
        return 2 * pol_idx + dim_idx

    calls = [
        call(
            subband_id=1,
            subband_data=StatMonitorData(
                real_pol_a_mean_freq_avg=mean_frequency_avg[_idx(POLA_IDX, REAL_IDX)],
                real_pol_a_variance_freq_avg=variance_frequency_avg[_idx(POLA_IDX, REAL_IDX)],
                real_pol_a_num_clipped_samples=num_clipped_samples[_idx(POLA_IDX, REAL_IDX)],
                imag_pol_a_mean_freq_avg=mean_frequency_avg[_idx(POLA_IDX, IMAG_IDX)],
                imag_pol_a_variance_freq_avg=variance_frequency_avg[_idx(POLA_IDX, IMAG_IDX)],
                imag_pol_a_num_clipped_samples=num_clipped_samples[_idx(POLA_IDX, IMAG_IDX)],
                real_pol_a_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[_idx(POLA_IDX, REAL_IDX)],
                real_pol_a_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[
                    _idx(POLA_IDX, REAL_IDX)
                ],
                real_pol_a_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[
                    _idx(POLA_IDX, REAL_IDX)
                ],
                imag_pol_a_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[_idx(POLA_IDX, IMAG_IDX)],
                imag_pol_a_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[
                    _idx(POLA_IDX, IMAG_IDX)
                ],
                imag_pol_a_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[
                    _idx(POLA_IDX, IMAG_IDX)
                ],
                real_pol_b_mean_freq_avg=mean_frequency_avg[_idx(POLB_IDX, REAL_IDX)],
                real_pol_b_variance_freq_avg=variance_frequency_avg[_idx(POLB_IDX, REAL_IDX)],
                real_pol_b_num_clipped_samples=num_clipped_samples[_idx(POLB_IDX, REAL_IDX)],
                imag_pol_b_mean_freq_avg=mean_frequency_avg[_idx(POLB_IDX, IMAG_IDX)],
                imag_pol_b_variance_freq_avg=variance_frequency_avg[_idx(POLB_IDX, IMAG_IDX)],
                imag_pol_b_num_clipped_samples=num_clipped_samples[_idx(POLB_IDX, IMAG_IDX)],
                real_pol_b_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[_idx(POLB_IDX, REAL_IDX)],
                real_pol_b_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[
                    _idx(POLB_IDX, REAL_IDX)
                ],
                real_pol_b_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[
                    _idx(POLB_IDX, REAL_IDX)
                ],
                imag_pol_b_mean_freq_avg_rfi_excised=mean_frequency_avg_rfi_excised[_idx(POLB_IDX, IMAG_IDX)],
                imag_pol_b_variance_freq_avg_rfi_excised=variance_frequency_avg_rfi_excised[
                    _idx(POLB_IDX, IMAG_IDX)
                ],
                imag_pol_b_num_clipped_samples_rfi_excised=num_clipped_samples_rfi_excised[
                    _idx(POLB_IDX, IMAG_IDX)
                ],
            ),
        )
    ]
    subband_monitor_data_callback.assert_has_calls(calls=calls)


def test_stat_grpc_go_to_fault(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    component_state_callback: MagicMock,
) -> None:
    """Test that  go_to_fault."""
    mock_servicer_context.go_to_fault = MagicMock(return_value=GoToFaultResponse())

    grpc_api.go_to_fault()

    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())
    component_state_callback.assert_called_once_with(obsfault=True)


@pytest.mark.parametrize(
    "tango_log_level,grpc_log_level",
    [
        (LoggingLevel.INFO, LogLevel.INFO),
        (LoggingLevel.DEBUG, LogLevel.DEBUG),
        (LoggingLevel.FATAL, LogLevel.CRITICAL),
        (LoggingLevel.WARNING, LogLevel.WARNING),
        (LoggingLevel.OFF, LogLevel.INFO),
    ],
)
def test_stat_grpc_api_set_log_level(
    grpc_api: PstStatProcessApiGrpc,
    mock_servicer_context: MagicMock,
    tango_log_level: LoggingLevel,
    grpc_log_level: LogLevel,
) -> None:
    """Test the set_logging_level on gRPC API."""
    response = SetLogLevelResponse()
    mock_servicer_context.set_log_level = MagicMock(return_value=response)
    log_level_request = SetLogLevelRequest(log_level=grpc_log_level)
    grpc_api.set_log_level(log_level=tango_log_level)
    mock_servicer_context.set_log_level.assert_called_once_with(log_level_request)
    mock_servicer_context.reset_mock()
