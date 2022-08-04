# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV API."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse

from ska_pst_lmc.receive.receive_process_api import PstReceiveProcessApi, PstReceiveProcessApiGrpc
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


@pytest.fixture
def grpc_api(
    client_id: str,
    grpc_endpoint: str,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    pst_lmc_service: TestPstLmcService,
    background_task_processor: BackgroundTaskProcessor,
) -> PstReceiveProcessApi:
    """Fixture to create instance of a gRPC API with client."""
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
    """Test that SMRB gRPC API connects to the server."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    grpc_api.connect()

    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=client_id))
