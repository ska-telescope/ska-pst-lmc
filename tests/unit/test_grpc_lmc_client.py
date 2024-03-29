# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module tests for gRPC LMC client not covered by other tests."""

import logging
from unittest.mock import MagicMock

import grpc
import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    BeamConfiguration,
    ErrorCode,
    GetBeamConfigurationRequest,
    GetBeamConfigurationResponse,
    GetEnvironmentRequest,
    GetEnvironmentResponse,
    GetScanConfigurationRequest,
    GetScanConfigurationResponse,
    GetStateRequest,
    GetStateResponse,
    GoToFaultRequest,
    GoToFaultResponse,
    LogLevel,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ObsState as GrpcObsState
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    ScanConfiguration,
    SetLogLevelRequest,
    SetLogLevelResponse,
    SmrbBeamConfiguration,
    SmrbScanConfiguration,
)
from ska_tango_base.control_model import ObsState

from ska_pst_lmc.component.grpc_lmc_client import (
    NotConfiguredForScanException,
    PstGrpcLmcClient,
    ResourcesNotAssignedException,
    UnknownGrpcException,
)
from ska_pst_lmc.test.test_grpc_server import TestMockException, TestPstLmcService


@pytest.fixture
def grpc_client(
    client_id: str,
    grpc_endpoint: str,
    logger: logging.Logger,
    pst_lmc_service: TestPstLmcService,
) -> PstGrpcLmcClient:
    """Fixture for getting instance of PstGrpcLmcClient."""
    # ensure the servicer context is reset.
    return PstGrpcLmcClient(client_id=client_id, endpoint=grpc_endpoint, logger=logger)


def test_grpc_client_get_beam_configuration(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Test getting the beam configuration of service."""
    response = GetBeamConfigurationResponse(
        beam_configuration=BeamConfiguration(smrb=SmrbBeamConfiguration())
    )
    mock_servicer_context.get_beam_configuration = MagicMock(return_value=response)
    grpc_client.get_beam_configuration()

    mock_servicer_context.get_beam_configuration.assert_called_once_with(GetBeamConfigurationRequest())


def test_grpc_client_get_beam_configuration_throws_exception(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
    logger: logging.Logger,
) -> None:
    """Test getting the beam configuration of service throws exception."""
    mock_servicer_context.get_beam_configuration.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_CONFIGURED_FOR_BEAM,
        message="Resource not assigned.",
    )

    with pytest.raises(ResourcesNotAssignedException):
        grpc_client.get_beam_configuration()


def test_grpc_client_get_scan_configuration(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Test getting the configuration for upcoming scan."""
    response = GetScanConfigurationResponse(
        scan_configuration=ScanConfiguration(smrb=SmrbScanConfiguration())
    )
    mock_servicer_context.get_scan_configuration = MagicMock(return_value=response)
    grpc_client.get_scan_configuration()

    mock_servicer_context.get_scan_configuration.assert_called_once_with(GetScanConfigurationRequest())


def test_grpc_client_get_scan_configuration_throws_exception(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Test getting the configuration for upcoming scan throws exception."""
    mock_servicer_context.get_scan_configuration.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.FAILED_PRECONDITION,
        error_code=ErrorCode.NOT_CONFIGURED_FOR_SCAN,
        message="Not configured for scan.",
    )

    with pytest.raises(NotConfiguredForScanException):
        grpc_client.get_scan_configuration()


def test_grpc_client_get_state(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Test getting the state of remote service."""
    response = GetStateResponse(state=GrpcObsState.IDLE)
    mock_servicer_context.get_state = MagicMock(return_value=response)
    client_response = grpc_client.get_state()

    mock_servicer_context.get_state.assert_called_once_with(GetStateRequest())
    assert client_response == ObsState.IDLE


def test_grpc_client_get_state_throws_exception(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Test getting the state of remote service throws exception."""
    mock_servicer_context.get_state.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Interal server error.",
    )

    with pytest.raises(UnknownGrpcException):
        grpc_client.get_state()


def test_grpc_client_go_to_fault(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Tests calling go_to_fault on remote service."""
    response = GoToFaultResponse()
    mock_servicer_context.go_to_fault = MagicMock(return_value=response)
    grpc_client.go_to_fault()

    mock_servicer_context.go_to_fault.assert_called_once_with(GoToFaultRequest())


def test_grpc_client_go_to_fault_throws_exception(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Tests calling go_to_fault on remote service."""
    mock_servicer_context.go_to_fault.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Interal server error.",
    )

    with pytest.raises(UnknownGrpcException):
        grpc_client.go_to_fault()


def test_grpc_client_get_env(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Test handles getting environment from remote system."""
    response = GetEnvironmentResponse()
    response.values["foo"].string_value = "bar"
    response.values["cat"].float_value = 0.5
    response.values["dog"].unsigned_int_value = 42
    response.values["bat"].signed_int_value = -10

    mock_servicer_context.get_env = MagicMock(return_value=response)
    client_response = grpc_client.get_env()
    expected_response = {
        "foo": "bar",
        "cat": 0.5,
        "dog": 42,
        "bat": -10,
    }

    mock_servicer_context.get_env.assert_called_once_with(GetEnvironmentRequest())
    assert expected_response == client_response


def test_grpc_client_get_env_throws_exception(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
) -> None:
    """Tests calling get_env on remote service throws a fault."""
    mock_servicer_context.get_env.side_effect = TestMockException(
        grpc_status_code=grpc.StatusCode.INTERNAL,
        message="Interal server error.",
    )

    with pytest.raises(UnknownGrpcException):
        grpc_client.get_env()


@pytest.mark.parametrize(
    "log_level", [LogLevel.INFO, LogLevel.DEBUG, LogLevel.CRITICAL, LogLevel.WARNING, LogLevel.INFO]
)
def test_grpc_client_set_log_level(
    grpc_client: PstGrpcLmcClient,
    mock_servicer_context: MagicMock,
    log_level: LogLevel,
) -> None:
    """Tests calling set_log_level on remote service."""
    response = SetLogLevelResponse()
    mock_servicer_context.set_log_level = MagicMock(return_value=response)
    log_level_request = SetLogLevelRequest(log_level=log_level)
    grpc_client.set_log_level(request=log_level_request)
    mock_servicer_context.set_log_level.assert_called_once_with(log_level_request)
    mock_servicer_context.reset_mock()
