# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV component managers class."""

import logging
import time
from typing import Callable
from unittest.mock import MagicMock, call

import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_tango_base.control_model import CommunicationStatus, SimulationMode

from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager
from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_process_api import (
    PstReceiveProcessApi,
    PstReceiveProcessApiGrpc,
    PstReceiveProcessApiSimulator,
)
from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources
from ska_pst_lmc.test import TestPstLmcService


@pytest.fixture
def component_manager(
    device_name: str,
    grpc_endpoint: str,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstReceiveProcessApi,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    recv_network_interface: str,
    recv_udp_port: int,
) -> PstReceiveComponentManager:
    """Create instance of a component manager."""
    return PstReceiveComponentManager(
        device_name=device_name,
        process_api_endpoint=grpc_endpoint,
        simulation_mode=simulation_mode,
        logger=logger,
        communication_state_callback=communication_state_callback,
        component_state_callback=component_state_callback,
        api=api,
        network_interface=recv_network_interface,
        udp_port=recv_udp_port,
    )


@pytest.fixture
def api(
    device_name: str,
    grpc_endpoint: str,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    component_state_callback: Callable,
) -> PstReceiveProcessApi:
    """Create an API instance."""
    if simulation_mode == SimulationMode.TRUE:
        return PstReceiveProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
    else:
        return PstReceiveProcessApiGrpc(
            client_id=device_name,
            grpc_endpoint=grpc_endpoint,
            logger=logger,
            component_state_callback=component_state_callback,
        )


@pytest.fixture
def monitor_data() -> ReceiveData:
    """Create an an instance of ReceiveData for monitor data."""
    from ska_pst_lmc.receive.receive_simulator import generate_random_update

    return generate_random_update()


@pytest.fixture
def calculated_receive_subband_resources(
    beam_id: int,
    assign_resources_request: dict,
    recv_network_interface: str,
    recv_udp_port: int,
) -> dict:
    """Calculate expected subband resources."""
    return calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )


def test_start_communicating_calls_connect_on_api(
    component_manager: PstReceiveComponentManager,
    api: PstReceiveProcessApi,
) -> None:
    """Assert start/stop communicating calls API."""
    api = MagicMock(wraps=api)
    component_manager._api = api

    component_manager.start_communicating()
    api.connect.assert_called_once()
    api.disconnect.assert_not_called()

    component_manager.stop_communicating()
    api.disconnect.assert_called_once()


@pytest.mark.parametrize(
    "property",
    [
        ("received_rate"),
        ("received_data"),
        ("dropped_rate"),
        ("dropped_data"),
        ("misordered_packets"),
        ("malformed_packets"),
        ("relative_weight"),
        ("relative_weights"),
    ],
)
def test_properties_come_from_api_monitor_data(
    component_manager: PstReceiveComponentManager,
    api: PstReceiveProcessApi,
    monitor_data: ReceiveData,
    property: str,
) -> None:
    """Test properties are coming from API monitor data."""
    api = MagicMock()
    type(api).monitor_data = monitor_data
    component_manager._api = api

    actual = getattr(component_manager, property)
    expected = getattr(monitor_data, property)

    assert actual == expected


def test_assign_resources(
    component_manager: PstReceiveComponentManager,
    assign_resources_request: dict,
    task_callback: Callable,
    calculated_receive_subband_resources: dict,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test that assign resources calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.assign(resources=assign_resources_request, task_callback=task_callback)

    expected_request = {
        "common": calculated_receive_subband_resources["common"],
        "subband": calculated_receive_subband_resources["subbands"][1],
    }

    api.assign_resources.assert_called_once_with(resources=expected_request, task_callback=task_callback)


def test_release_resources(
    component_manager: PstReceiveComponentManager,
    task_callback: Callable,
) -> None:
    """Test that assign resources calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.release_all(task_callback=task_callback)

    api.release_resources.assert_called_once_with(task_callback=task_callback)


def test_api_instance_changes_depending_on_simulation_mode(
    component_manager: PstReceiveComponentManager,
) -> None:
    """Test to assert that the process API changes depending on simulation mode."""
    assert component_manager.simulation_mode == SimulationMode.TRUE
    assert type(component_manager._api) == PstReceiveProcessApiSimulator

    component_manager.simulation_mode = SimulationMode.FALSE

    assert type(component_manager._api) == PstReceiveProcessApiGrpc


@pytest.mark.parametrize(
    "simulation_mode",
    [
        (SimulationMode.TRUE,),
        (SimulationMode.FALSE,),
    ],
)
def test_no_change_in_simulation_mode_value_wont_change_communication_state(
    device_name: str,
    component_manager: PstReceiveComponentManager,
    simulation_mode: SimulationMode,
    pst_lmc_service: TestPstLmcService,
    mock_servicer_context: MagicMock,
) -> None:
    """Test no change in simulation mode does not change communication state."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    component_manager._update_communication_state = update_communication_state

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == simulation_mode

    component_manager.start_communicating()
    time.sleep(0.1)
    assert component_manager.communication_state == CommunicationStatus.ESTABLISHED
    if simulation_mode == SimulationMode.FALSE:
        mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=device_name))

    calls = [call(CommunicationStatus.NOT_ESTABLISHED), call(CommunicationStatus.ESTABLISHED)]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = simulation_mode
    update_communication_state.assert_not_called()


def test_if_communicating_switching_simulation_mode_must_stop_then_restart(
    device_name: str,
    component_manager: PstReceiveComponentManager,
    pst_lmc_service: TestPstLmcService,
    mock_servicer_context: MagicMock,
) -> None:
    """Test if communicating and simulation mode changes, then need to reconnect."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    component_manager._update_communication_state = update_communication_state

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == SimulationMode.TRUE

    component_manager.start_communicating()
    time.sleep(0.1)
    assert component_manager.communication_state == CommunicationStatus.ESTABLISHED

    calls = [call(CommunicationStatus.NOT_ESTABLISHED), call(CommunicationStatus.ESTABLISHED)]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.FALSE
    time.sleep(0.1)
    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=device_name))

    calls = [
        call(CommunicationStatus.DISABLED),
        call(CommunicationStatus.NOT_ESTABLISHED),
        call(CommunicationStatus.ESTABLISHED),
    ]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.TRUE
    time.sleep(0.1)
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()


def test_not_communicating_switching_simulation_mode_not_try_to_establish_connection(
    component_manager: PstReceiveComponentManager,
) -> None:
    """Test if not communicating and change of simulation happens, don't do anything."""
    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    component_manager._update_communication_state = update_communication_state

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == SimulationMode.TRUE

    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.FALSE
    update_communication_state.assert_not_called()
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.TRUE
    update_communication_state.assert_not_called()
