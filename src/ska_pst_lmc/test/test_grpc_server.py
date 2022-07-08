# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for implementing a test implementations of the gRPC LMC service."""

from __future__ import annotations

import logging
from concurrent import futures
from types import TracebackType
from typing import Any, Optional, Type

import grpc
import tango
from grpc import ServicerContext
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceServicer, add_PstLmcServiceServicer_to_server

__all__ = [
    "TestMockServicer",
    "TestPstLmcService",
]


class TestMockServicer(PstLmcServiceServicer):
    """Test Servicer that acts on the requests sent to the test server.

    This is meant to be used within testing frameworks to allow asserting
    that the API is called.
    """

    # Disable PyTest thinking class is test suite class
    __test__: bool = False

    def __init__(self: TestMockServicer, context: Any) -> None:
        """Initialise the test mock servicer.

        All requests will be delegated to the context parameter which
        should be a mock that can then be used to assert calls and
        can return results when called.

        :param context: this should be any object that can be used
            to assert or create errors (i.e. a mock).
        """
        self._context = context

    def connect(
        self: TestMockServicer, request: ConnectionRequest, context: ServicerContext
    ) -> ConnectionResponse:
        """Handle connection request from client."""
        return self._context.connect(request)


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
        servicer: PstLmcServiceServicer,
        port: int,
        interface: str = "0.0.0.0",
        max_workers: int = 10,
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
        self._thread_pool = futures.ThreadPoolExecutor(max_workers=max_workers)
        self._server = grpc.server(self._thread_pool)
        self._port = port
        self._interface = interface
        self._logger = logger or logging.getLogger(__name__)
        add_PstLmcServiceServicer_to_server(servicer=servicer, server=self._server)
        self._future: Optional[futures.Future] = None

    def __del__(self: TestPstLmcService) -> None:
        """Drop of the instance has been requested."""
        self.stop()

    def __enter__(self: TestPstLmcService) -> TestPstLmcService:
        """Use service as a context manager."""
        self.serve()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Exit from context manager."""
        self.stop()

    def _serve(self: TestPstLmcService) -> None:
        """Start the gRPC to serve."""
        self._logger.info("Starting server")
        try:
            self._server.add_insecure_port(f"{self._interface}:{self._port}")
            self._server.start()
            self._server.wait_for_termination()
        except futures.CancelledError:
            self._logger.debug("Serve task has been cancelled.")
        except KeyboardInterrupt:
            self._logger.debug("Interrupt has been requested. Exiting serve")
        except Exception:
            self._logger.error("Unknown exception has happened while serving.", exc_info=True)
        finally:
            self._future = None

    def serve(self: TestPstLmcService) -> None:
        """Start the background serving of requests."""
        with tango.EnsureOmniThread():
            self._future = self._thread_pool.submit(self._serve)

    def stop(self: TestPstLmcService) -> None:
        """Stop the background serving of requests."""
        self._server.stop(0.1)
        if self._future:
            self._future.cancel()
