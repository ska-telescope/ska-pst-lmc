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

from ska_pst_lmc.smrb.smrb_component_manager import PstSmrbComponentManager
from ska_pst_lmc.smrb.smrb_model import SharedMemoryRingBufferData
from ska_pst_lmc.smrb.smrb_process_api import (
    PstSmrbProcessApi,
    PstSmrbProcessApiGrpc,
    PstSmrbProcessApiSimulator,
)
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService


@pytest.fixture
def component_manager(
    device_name: str,
    grpc_endpoint: str,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstSmrbProcessApi,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
) -> PstSmrbComponentManager:
    """Create instance of a component manager."""
    return PstSmrbComponentManager(
        device_name=device_name,
        process_api_endpoint=grpc_endpoint,
        simulation_mode=simulation_mode,
        logger=logger,
        communication_state_callback=communication_state_callback,
        component_state_callback=component_state_callback,
        api=api,
    )


@pytest.fixture
def api(
    device_name: str,
    grpc_endpoint: str,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    component_state_callback: Callable,
) -> PstSmrbProcessApi:
    """Create an API instance."""
    if simulation_mode == SimulationMode.TRUE:
        return PstSmrbProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
    else:
        return PstSmrbProcessApiGrpc(
            client_id=device_name,
            grpc_endpoint=grpc_endpoint,
            logger=logger,
            component_state_callback=component_state_callback,
        )


@pytest.fixture
def monitor_data() -> SharedMemoryRingBufferData:
    """Create an an instance of ReceiveData for monitor data."""
    from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator

    simulator = PstSmrbSimulator()
    simulator.scan(args={})

    return simulator.get_data()


def test_start_communicating_calls_connect_on_api(
    component_manager: PstSmrbComponentManager,
    api: PstSmrbProcessApi,
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
    "simulation_mode, property",
    [
        (SimulationMode.TRUE, "ring_buffer_utilisation"),
        (SimulationMode.TRUE, "ring_buffer_size"),
        (SimulationMode.TRUE, "number_subbands"),
        (SimulationMode.TRUE, "subband_ring_buffer_utilisations"),
        (SimulationMode.TRUE, "subband_ring_buffer_sizes"),
        (SimulationMode.FALSE, "ring_buffer_utilisation"),
        (SimulationMode.FALSE, "ring_buffer_size"),
        (SimulationMode.FALSE, "number_subbands"),
        (SimulationMode.FALSE, "subband_ring_buffer_utilisations"),
        (SimulationMode.FALSE, "subband_ring_buffer_sizes"),
    ],
)
def test_properties_come_from_simulator_api_monitor_data(
    component_manager: PstSmrbComponentManager,
    simulation_mode: SimulationMode,
    api: PstSmrbProcessApi,
    monitor_data: SharedMemoryRingBufferData,
    property: str,
) -> None:
    """Test properties are coming from API monitor data."""
    if simulation_mode == SimulationMode.TRUE:
        assert type(api) == PstSmrbProcessApiSimulator
    else:
        assert type(api) == PstSmrbProcessApiGrpc

    # mock the API as we don't need to call it.
    api = MagicMock()
    type(api).monitor_data = monitor_data
    component_manager._api = api

    actual = getattr(component_manager, property)
    expected = getattr(monitor_data, property)

    assert actual == expected


def test_api_instance_changes_depending_on_simulation_mode(
    component_manager: PstSmrbComponentManager,
) -> None:
    """Test to assert that the process API changes depending on simulation mode."""
    assert component_manager.simulation_mode == SimulationMode.TRUE
    assert type(component_manager._api) == PstSmrbProcessApiSimulator

    component_manager.simulation_mode = SimulationMode.FALSE

    assert type(component_manager._api) == PstSmrbProcessApiGrpc


@pytest.mark.parametrize(
    "simulation_mode",
    [
        (SimulationMode.TRUE,),
        (SimulationMode.FALSE,),
    ],
)
def test_no_change_in_simulation_mode_value_wont_change_communication_state(
    device_name: str,
    component_manager: PstSmrbComponentManager,
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
    component_manager: PstSmrbComponentManager,
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
    component_manager: PstSmrbComponentManager,
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


# need test to see that it uses the API's
