# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for implementing a test implementations of the gRPC LMC service."""

from __future__ import annotations

import logging
import time
from concurrent import futures
from dataclasses import dataclass
from typing import Any, Generator, Optional

import grpc
from grpc import ServicerContext
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AbortRequest,
    AbortResponse,
    AssignResourcesRequest,
    AssignResourcesResponse,
    ConnectionRequest,
    ConnectionResponse,
    EndScanRequest,
    EndScanResponse,
    ErrorCode,
    MonitorRequest,
    MonitorResponse,
    ReleaseResourcesRequest,
    ReleaseResourcesResponse,
    ResetRequest,
    ResetResponse,
    ScanRequest,
    ScanResponse,
    Status,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceServicer

from ska_pst_lmc.component.grpc_lmc_client import GRPC_STATUS_DETAILS_METADATA_KEY

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

    def assign_resources(
        self: TestMockServicer, request: AssignResourcesRequest, context: ServicerContext
    ) -> AssignResourcesResponse:
        """Handle assign resources."""
        self._logger.debug("assign_resources request")
        try:
            return self._context.assign_resources(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def release_resources(
        self: TestMockServicer, request: ReleaseResourcesRequest, context: ServicerContext
    ) -> ReleaseResourcesResponse:
        """Handle release resources."""
        self._logger.debug("release_resources request")
        try:
            return self._context.release_resources(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def scan(self: TestMockServicer, request: ScanRequest, context: ServicerContext) -> ScanResponse:
        """Handle scan."""
        self._logger.debug("scan request")
        try:
            return self._context.scan(request)
        except TestMockException as e:
            context.abort_with_status(e.as_grpc_status())
            assert False, "Unreachable"

    def end_scan(
        self: TestMockServicer, request: EndScanRequest, context: ServicerContext
    ) -> EndScanResponse:
        """Handle end scan."""
        self._logger.debug("end_scan request")
        try:
            return self._context.end_scan(request)
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

    def __del__(self: TestPstLmcService) -> None:
        """Drop of the instance has been requested."""
        self.stop()

    def serve(self: TestPstLmcService) -> None:
        """Start the gRPC to serve."""
        self._logger.info("Starting server")
        try:
            self._server.start()
            self._running = True
            self._server.wait_for_termination()
            self._running = False
            self._logger.debug("Server has terminated")
        except futures.CancelledError:
            self._logger.debug("Serve task has been cancelled.")
        except KeyboardInterrupt:
            self._logger.debug("Interrupt has been requested. Exiting serve")
        except Exception:
            self._logger.error("Unknown exception has happened while serving.", exc_info=True)

    def stop(self: TestPstLmcService) -> None:
        """Stop the background serving of requests."""
        if self._running:
            self._logger.debug("Stopping test gRPC service.")
            self._server.stop(grace=0.1)
            time.sleep(0.2)
            self._logger.debug("Service stopped.")
