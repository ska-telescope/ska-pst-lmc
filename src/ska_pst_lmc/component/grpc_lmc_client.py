# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the gRPC LMC client to external processes."""

from __future__ import annotations

import logging
from typing import Any, Optional

import grpc
from grpc import Channel
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AssignResourcesRequest,
    ConnectionRequest,
    ErrorCode,
    GetAssignedResourcesRequest,
    GetAssignedResourcesResponse,
    ReleaseResourcesRequest,
    Status,
)
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceStub

GRPC_STATUS_DETAILS_METADATA_KEY = "grpc-status-details-bin"


class ResourcesAlreadyAssignedException(Exception):
    """Exception for when resources were already assigned.

    Raised when the server is already in an assigned resources state
    and the request should not have been called.
    """

    def __init__(self: ResourcesAlreadyAssignedException, message: str) -> None:
        """Initialise exception."""
        self.message = message
        super().__init__()


class ResourcesNotAssignedException(Exception):
    """Exception for when resources have not been assigned.

    Raised when the server does not have any resources assigned. This
    request should not have been called.
    """

    def __init__(self: ResourcesNotAssignedException, message: str) -> None:
        """Initialise exception."""
        self.message = message
        super().__init__()


class InvalidRequestException(Exception):
    """Exception with the actual request parameters.

    This is raised when the server validates the request and request is
    not correct, such as the assign resources message has a protobuf
    Oneof field for resources and the incorrect one was applied.
    """

    def __init__(self: InvalidRequestException, message: str) -> None:
        """Initialise exception."""
        self.message = message
        super().__init__()


class ServerError(Exception):
    """Exception when an exception on the server side happens.

    The server raised an exception during the processing of the request
    and the logs of the server should be checked. The client is not
    expected to handle this exception.
    """

    def __init__(self: ServerError, error_code: int, message: str) -> None:
        """Initialise exception."""
        self.error_code = error_code
        self.message = message
        super().__init__()


class UnknownGrpcException(Exception):
    """An unknown gRPC exception.

    This error occurs due to gRPC itself. The client is not
    expected to handle this request.
    """

    def __init__(self: UnknownGrpcException, error_code: int, message: str) -> None:
        """Initialise exception."""
        self.error_code = error_code
        self.message = message
        super().__init__()


def _handle_grpc_error(error: grpc.RpcError) -> None:
    if hasattr(error, "trailing_metadata"):
        for k, v in error.trailing_metadata():
            if k == GRPC_STATUS_DETAILS_METADATA_KEY:
                msg = Status()
                msg.ParseFromString(v)

                error_code = msg.code
                if error_code == ErrorCode.INVALID_REQUEST:
                    raise InvalidRequestException(msg.message) from error
                elif error_code == ErrorCode.RESOURCES_ALREADY_ASSIGNED:
                    raise ResourcesAlreadyAssignedException(msg.message) from error
                elif error_code == ErrorCode.RESOURCES_NOT_ASSIGNED:
                    raise ResourcesNotAssignedException(msg.message) from error
                else:
                    if hasattr(error, "code"):
                        error_code = error.code()
                    raise ServerError(error_code, msg.message()) from error

    if hasattr(error, "code"):
        error_code = error.code()
    else:
        error_code = -1

    raise UnknownGrpcException(error_code, error.message()) from error


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
            assert False, "unreachable"

    def release_resources(self: PstGrpcLmcClient) -> bool:
        """Call release_resources on remote gRPC service."""
        self._logger.debug("Releasing component resources")
        try:
            self._service.release_resources(ReleaseResourcesRequest())
            return True
        except grpc.RpcError as e:
            _handle_grpc_error(e)
            assert False, "unreachable"

    def get_assigned_resources(self: PstGrpcLmcClient) -> GetAssignedResourcesResponse:
        """Call get_assigned_resources on remote gRPC service."""
        self._logger.debug("Getting assigned resources.")
        try:
            request: GetAssignedResourcesRequest = GetAssignedResourcesRequest()
            return self._service.get_assigned_resources(request)
        except grpc.RpcError as e:
            _handle_grpc_error(e)
