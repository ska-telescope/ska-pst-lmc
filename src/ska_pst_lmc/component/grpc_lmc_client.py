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
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceStub


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
        self: PstLmcServiceStub,
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

    def connect(self: PstLmcServiceStub) -> bool:
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
