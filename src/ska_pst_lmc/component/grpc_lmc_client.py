# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the gRPC LMC client to external processes."""

from __future__ import annotations

import logging
from threading import Event
from typing import Any, Dict, Generator, NoReturn, Optional, Type

import grpc
from grpc import Channel
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AssignResourcesRequest,
    ConnectionRequest,
    EndScanRequest,
    ErrorCode,
    GetAssignedResourcesRequest,
    GetAssignedResourcesResponse,
    GetStateRequest,
    GetStateResponse,
    MonitorRequest,
    MonitorResponse,
    ReleaseResourcesRequest,
    ScanRequest,
    Status,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceStub
from ska_tango_base.control_model import ObsState

from ska_pst_lmc.util.timeout_iterator import TimeoutIterator

GRPC_STATUS_DETAILS_METADATA_KEY = "grpc-status-details-bin"


class BaseGrpcException(Exception):
    """Base exception to capture gRPC related exceptions."""

    def __init__(self: BaseGrpcException, message: str) -> None:
        """Initialise exception."""
        self.message = message
        super().__init__()


class AlreadyScanningException(BaseGrpcException):
    """Exception for when the process is already scanning.

    Raised when the server is already scanning and is in the
    SCANNING ObsState state. If this exception is raised
    it is likely due to a mismatch in the state model of the
    LMC and the server, which could be the case if a command
    line interface has interacted with the server directly.

    The LMC can recover from this as it should only be raised
    when the scan command is called. The LMC should log this
    happened but can safely go into SCANNING state.
    """


class NotScanningException(BaseGrpcException):
    """Exception for when tyring to end scan but component is not scanning.

    Raised when the server is not in a scanning state but received an
    end scan command. Just like :py:class:`AlreadyScanningException`
    it is possible for the LMC to recover from this as this exception
    is only raised during end_scan. The LMC should log this happened
    but can safely go into a READY state.
    """


class ResourcesAlreadyAssignedException(BaseGrpcException):
    """Exception for when resources were already assigned.

    Raised when the server is already in an assigned resources state
    and the request should not have been called.
    """


class ResourcesNotAssignedException(BaseGrpcException):
    """Exception for when resources have not been assigned.

    Raised when the server does not have any resources assigned. This
    request should not have been called.
    """


class InvalidRequestException(BaseGrpcException):
    """Exception with the actual request parameters.

    This is raised when the server validates the request and request is
    not correct, such as the assign resources message has a protobuf
    Oneof field for resources and the incorrect one was applied.
    """


class ServerError(BaseGrpcException):
    """Exception when an exception on the server side happens.

    The server raised an exception during the processing of the request
    and the logs of the server should be checked. The client is not
    expected to handle this exception.
    """

    def __init__(self: ServerError, error_code: int, message: str) -> None:
        """Initialise exception."""
        self.error_code = error_code
        super().__init__(message)


class UnknownGrpcException(BaseGrpcException):
    """An unknown gRPC exception.

    This error occurs due to gRPC itself. The client is not
    expected to handle this request.
    """

    def __init__(self: UnknownGrpcException, error_code: int, message: str) -> None:
        """Initialise exception."""
        self.error_code = error_code
        super().__init__(message)


ERROR_CODE_EXCEPTION_MAP: Dict[ErrorCode, Type[BaseGrpcException]] = {
    ErrorCode.ALREADY_SCANNING: AlreadyScanningException,
    ErrorCode.NOT_SCANNING: NotScanningException,
    ErrorCode.INVALID_REQUEST: InvalidRequestException,
    ErrorCode.RESOURCES_ALREADY_ASSIGNED: ResourcesAlreadyAssignedException,
    ErrorCode.RESOURCES_NOT_ASSIGNED: ResourcesNotAssignedException,
}


def _handle_grpc_error(error: grpc.RpcError) -> NoReturn:
    if hasattr(error, "trailing_metadata"):
        for k, v in error.trailing_metadata():
            if k == GRPC_STATUS_DETAILS_METADATA_KEY:
                msg = Status()
                msg.ParseFromString(v)

                error_code = msg.code
                if error_code in ERROR_CODE_EXCEPTION_MAP:
                    raise ERROR_CODE_EXCEPTION_MAP[error_code](msg.message) from error
                else:
                    if hasattr(error, "code"):
                        error_code = error.code()
                    raise ServerError(error_code, msg.message) from error

    if hasattr(error, "code"):
        error_code = error.code()
    else:
        error_code = -1

    raise UnknownGrpcException(error_code, error.details()) from error


class PstGrpcLmcClient:
    """The client API that connects to a remote gRPC service.

    This client is a wrapper around the :py:class:`PstLmcServiceStub`
    that is generated from the gRPC/Protobuf bindings.

    Once fully implemented this class will be able to be used by
    any of the LMC components :py:class:`PstProcessApi` implementations.
    """

    _client_id: str
    _channel: Channel
    _endpoint: str
    _service: PstLmcServiceStub
    _logger: logging.Logger

    def __init__(
        self: PstGrpcLmcClient,
        client_id: str,
        endpoint: str,
        logger: Optional[logging.Logger],
        **kwargs: Any,
    ) -> None:
        """Initialise gRPC client.

        :param client_id: the ID of the client.
        :param endpoint: the endpoint of the service that this client is to communicate with.
        :param logger: the logger to use within this instance.
        """
        self._logger = logger or logging.getLogger(__name__)
        self._client_id = client_id
        self._endpoint = endpoint
        self._logger.info(f"Connecting '{client_id}' to remote endpoint '{endpoint}'")
        self._channel = grpc.insecure_channel(endpoint, options=[("wait_for_ready", True)])
        self._service = PstLmcServiceStub(channel=self._channel)

    def connect(self: PstGrpcLmcClient) -> bool:
        """Connect client to the remote server.

        This is used to let the server know that a client has connected.
        """
        self._logger.debug(f"Connect called for client {self._client_id}")
        request = ConnectionRequest(client_id=self._client_id)
        try:
            self._service.connect(request)
            return True
        except grpc.RpcError:
            self._logger.warning(f"Error in connecting to remote server {self._endpoint}", exc_info=True)
            raise

    def assign_resources(self: PstGrpcLmcClient, request: AssignResourcesRequest) -> bool:
        """Call assign_resources on remote gRPC service."""
        self._logger.debug("Assigning resources.")
        try:
            self._service.assign_resources(request)
            return True
        except grpc.RpcError as e:
            _handle_grpc_error(e)

    def release_resources(self: PstGrpcLmcClient) -> bool:
        """Call release_resources on remote gRPC service."""
        self._logger.debug("Releasing component resources")
        try:
            self._service.release_resources(ReleaseResourcesRequest())
            return True
        except grpc.RpcError as e:
            _handle_grpc_error(e)

    def get_assigned_resources(self: PstGrpcLmcClient) -> GetAssignedResourcesResponse:
        """Call get_assigned_resources on remote gRPC service."""
        self._logger.debug("Getting assigned resources.")
        try:
            request: GetAssignedResourcesRequest = GetAssignedResourcesRequest()
            return self._service.get_assigned_resources(request)
        except grpc.RpcError as e:
            _handle_grpc_error(e)

    def scan(self: PstGrpcLmcClient) -> bool:
        """Call scan on remote gRPC service."""
        self._logger.debug("Calling scan")
        try:
            self._service.scan(ScanRequest())
            return True
        except grpc.RpcError as e:
            _handle_grpc_error(e)

    def end_scan(self: PstGrpcLmcClient) -> bool:
        """Call scan on remote gRPC service."""
        self._logger.debug("Calling end scan")
        try:
            self._service.end_scan(EndScanRequest())
            return True
        except grpc.RpcError as e:
            _handle_grpc_error(e)

    def get_state(self: PstGrpcLmcClient) -> ObsState:
        """Call scan on remote gRPC service."""
        self._logger.debug("Calling get state")
        try:
            result: GetStateResponse = self._service.get_state(GetStateRequest())
            return ObsState(result.state)
        except grpc.RpcError as e:
            _handle_grpc_error(e)

    def monitor(
        self: PstGrpcLmcClient,
        polling_rate: int = 5000,
        abort_event: Optional[Event] = None,
    ) -> Generator[MonitorResponse, None, None]:
        """Call monitor on reqmore gRPC service.

        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring.
        """
        self._logger.debug("Calling monitor")
        try:
            self._monitor_stream = TimeoutIterator(
                iterator=self._service.monitor(MonitorRequest(polling_rate=polling_rate)),
                timeout=2.0 * polling_rate / 1000.0,  # convert to seconds and double
                abort_event=abort_event,
                expected_rate=polling_rate / 1000.0,
            )
            for t in self._monitor_stream:
                yield t

        except TimeoutError:
            pass

        except grpc.RpcError as e:
            _handle_grpc_error(e)
