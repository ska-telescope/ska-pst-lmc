# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for implementing a test implementations of the gRPC LMC service."""

from __future__ import annotations

import logging
import threading
from concurrent import futures
from dataclasses import dataclass
from typing import Any, Callable, Generator, Optional

import grpc
from grpc import ServicerContext
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AbortRequest,
    AbortResponse,
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
    GetBeamConfigurationRequest,
    GetBeamConfigurationResponse,
    GetEnvironmentRequest,
    GetEnvironmentResponse,
    GetLogLevelRequest,
    GetLogLevelResponse,
    GetScanConfigurationRequest,
    GetScanConfigurationResponse,
    GetStateRequest,
    GetStateResponse,
    GoToFaultRequest,
    GoToFaultResponse,
    MonitorRequest,
    MonitorResponse,
    ResetRequest,
    ResetResponse,
    SetLogLevelRequest,
    SetLogLevelResponse,
    StartScanRequest,
    StartScanResponse,
    Status,
    StopScanRequest,
    StopScanResponse,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceServicer

from ska_pst_lmc.component.grpc_lmc_client import GRPC_STATUS_DETAILS_METADATA_KEY
from ska_pst_lmc.util.callback import callback_safely

__all__ = [
    "TestMockServicer",
    "TestPstLmcService",
]


@dataclass
class TestGrpcStatus(grpc.Status):
    code: grpc.StatusCode
    details: str
    trailing_metadata: Optional[Any] = None


class TestMockException(Exception):

    # Disable PyTest thinking class is test suite class
    __test__: bool = False

    def __init__(
        self: TestMockException,
        grpc_status_code: grpc.StatusCode,
        message: str,
        error_code: Optional[ErrorCode] = None,
    ) -> None:
        self.grpc_status_code = grpc_status_code
        self.error_code = error_code
        self.message = message

    def as_grpc_status(self: TestMockException) -> TestGrpcStatus:
        if self.error_code:
            status = Status(code=self.error_code, message=self.message)
            return TestGrpcStatus(
                code=self.grpc_status_code,
                details=self.message,
                trailing_metadata=((GRPC_STATUS_DETAILS_METADATA_KEY, status.SerializeToString()),),
            )
        else:
            return TestGrpcStatus(
                code=self.grpc_status_code,
                details=self.message,
            )


class TestMockServicer(PstLmcServiceServicer):
    """Test Servicer that acts on the requests sent to the test server.

    This is meant to be used within testing frameworks to allow asserting
    that the API is called.
    """

    # Disable PyTest thinking class is test suite class
    __test__: bool = False

    def __init__(
        self: TestMockServicer,
        context: Any,
        logger: logging.Logger,
    ) -> None:
        """Initialise the test mock servicer.

        All requests will be delegated to the context parameter which
        should be a mock that can then be used to assert calls and
        can return results when called.

        :param context: this should be any object that can be used
            to assert or create errors (i.e. a mock).
        """
        self._context = context
        self._logger = logger

    def connect(
        self: TestMockServicer, request: ConnectionRequest, context: ServicerContext
    ) -> ConnectionResponse:
        """Handle connection request from client."""
        self._logger.debug("connect request")
        return self._context.connect(request)

    def configure_beam(
        self: TestMockServicer, request: ConfigureBeamRequest, context: ServicerContext
    ) -> ConfigureBeamResponse:
        """Handle assign resources."""
        self._logger.debug("configure_beam request")
        try:
            return self._context.configure_beam(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def deconfigure_beam(
        self: TestMockServicer, request: DeconfigureBeamRequest, context: ServicerContext
    ) -> DeconfigureBeamResponse:
        """Handle release resources."""
        self._logger.debug("deconfigure_beam request")
        try:
            return self._context.deconfigure_beam(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def get_beam_configuration(
        self: TestMockServicer, request: GetBeamConfigurationRequest, context: ServicerContext
    ) -> GetBeamConfigurationResponse:
        """Handle getting the assigned resources."""
        self._logger.debug("get_beam_configuration called.")
        try:
            return self._context.get_beam_configuration(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def configure_scan(
        self: TestMockServicer, request: ConfigureScanRequest, context: ServicerContext
    ) -> ConfigureScanResponse:
        """Handle configure request."""
        self._logger.debug("configure request")
        try:
            return self._context.configure_scan(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def deconfigure_scan(
        self: TestMockServicer, request: DeconfigureScanRequest, context: ServicerContext
    ) -> DeconfigureScanResponse:
        """Handle deconfigure request."""
        self._logger.debug("configure request")
        try:
            return self._context.deconfigure_scan(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def get_scan_configuration(
        self: TestMockServicer, request: GetScanConfigurationRequest, context: ServicerContext
    ) -> GetScanConfigurationResponse:
        """Handle getting the scan configuration."""
        self._logger.debug("get_scan_configuration called.")
        try:
            return self._context.get_scan_configuration(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def start_scan(
        self: TestMockServicer, request: StartScanRequest, context: ServicerContext
    ) -> StartScanResponse:
        """Handle scan."""
        self._logger.debug("scan request")
        try:
            return self._context.start_scan(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def stop_scan(
        self: TestMockServicer, request: StopScanRequest, context: ServicerContext
    ) -> StopScanResponse:
        """Handle end scan."""
        self._logger.debug("stop_scan request")
        try:
            return self._context.stop_scan(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def abort(self: TestMockServicer, request: AbortRequest, context: ServicerContext) -> AbortResponse:
        """Handle end scan."""
        self._logger.debug("abort requested")
        try:
            return self._context.abort(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def reset(self: TestMockServicer, request: ResetRequest, context: ServicerContext) -> ResetResponse:
        """Handle reset."""
        self._logger.debug("reset requested")
        try:
            return self._context.reset(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def get_state(
        self: TestMockServicer, request: GetStateRequest, context: ServicerContext
    ) -> GetStateResponse:
        """Handle getting the state of the service."""
        self._logger.debug("get_state called.")
        try:
            return self._context.get_state(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def go_to_fault(
        self: TestMockServicer, request: GoToFaultRequest, context: ServicerContext
    ) -> GoToFaultResponse:
        """Handle putting service into FAULT state."""
        self._logger.debug("go_to_fault called.")
        try:
            return self._context.go_to_fault(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def monitor(
        self: TestMockServicer, request: MonitorRequest, context: ServicerContext
    ) -> Generator[MonitorResponse, None, None]:
        """Handle monitor."""
        self._logger.debug("monitor request")
        try:
            return self._context.monitor(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def get_env(
        self: TestMockServicer, request: GetEnvironmentRequest, context: ServicerContext
    ) -> GetEnvironmentResponse:
        """Get environment."""
        self._logger.debug("get_env")
        try:
            return self._context.get_env(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def set_log_level(
        self: TestMockServicer, request: SetLogLevelRequest, context: ServicerContext
    ) -> SetLogLevelResponse:
        """Set Log Level."""
        self._logger.debug("set_log_level")
        try:
            return self._context.set_log_level(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def get_log_level(
        self: TestMockServicer, request: GetLogLevelRequest, context: ServicerContext
    ) -> GetLogLevelResponse:
        """Get Log Level."""
        self._logger.debug("get_log_level")
        try:
            return self._context.get_log_level(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"


class TestPstLmcService:
    """The service class for testing the gRPC LMC service.

    This class is designed to be used in unit testing but having instances
    of the :py:class:`TestMockServicer` passed in as a parameter or can be
    used in an integration test where this could be run dependently with
    specific instances of a :py:class:`PstLmcServiceServicer`. For now
    there is only the TestMockServicer that has been implemented.
    """

    # Disable PyTest thinking class is test suite class
    __test__: bool = False

    def __init__(
        self: TestPstLmcService,
        grpc_server: grpc.Server,
        logger: Optional[logging.Logger] = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the service.

        This uses a `futures.ThreadPoolExecutor` to create a gRPC server that
        exposes an API by the servicer instance that is provided.  The service
        is exposed on a given port and can listen on a given interface or all.

        :param servicer: the :py:class:`PstLmcServiceServicer` that provides the
            implementation of the service.
        :param port: the port that the service listens on.
        :param interface: the network interface (NIC) that the service should listen
            on.  If not supplied, "0.0.0.0" will be used.
        :param max_workers: the maximum number of workers the thread pool will use.
        :param logger: the logger to use with the class.
        """
        self._logger = logger or logging.getLogger(__name__)
        self._server = grpc_server
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def __del__(self: TestPstLmcService) -> None:
        """Drop of the instance has been requested."""
        self.stop()

    def _serve(self: TestPstLmcService, started_callback: Optional[Callable] = None) -> None:
        """Start the gRPC to serve."""
        self._logger.info("Starting server")
        try:
            self._server.start()
            self._running = True
            callback_safely(started_callback)
            self._server.wait_for_termination()
            self._running = False
            self._logger.debug("Server has terminated")
        except futures.CancelledError:
            self._logger.debug("Serve task has been cancelled.")
        except KeyboardInterrupt:
            self._logger.debug("Interrupt has been requested. Exiting serve")
        except Exception:
            self._logger.error("Unknown exception has happened while serving.", exc_info=True)

    def serve(self: TestPstLmcService, started_callback: Optional[Callable] = None) -> None:
        """Start the gRPC server to serve requests.

        This method should be called synchronously as this method will set up the gRPC in
        a background thread itself.  If the client wants to be notified when the background
        thread is serving then a started_callback should be passed.

        :param started_callback: a callback that will be called when the background thread
            is running, defaults to None.
        :type started_callback: Optional[Callable], optional
        """
        t = threading.Thread(target=self._serve, args=(started_callback,))
        t.start()
        self._thread = t

    def stop(self: TestPstLmcService) -> None:
        """Stop the background serving of requests."""
        if self._running:
            self._logger.debug("Stopping test gRPC service.")
            self._server.stop(grace=None)
            self._logger.debug("Service stopped.")

        if self._thread is not None:
            self._thread.join()
            self._thread = None
