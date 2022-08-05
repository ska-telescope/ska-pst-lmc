# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV component managers class."""

import logging
from typing import Callable
from unittest.mock import MagicMock

import pytest
from ska_tango_base.control_model import CommunicationStatus, SimulationMode

from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager
from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_process_api import (
    PstReceiveProcessApi,
    PstReceiveProcessApiGrpc,
    PstReceiveProcessApiSimulator,
)
from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources


@pytest.fixture
def component_manager(
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstReceiveProcessApi,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
) -> PstReceiveComponentManager:
    """Create instance of a component manager."""
    return PstReceiveComponentManager(
        device_name="test/recv/1",
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
def calculated_receive_subband_resources(beam_id: int, assign_resources_request: dict) -> dict:
    """Calculate expected subband resources."""
    return calculate_receive_subband_resources(beam_id=beam_id, request_params=assign_resources_request)


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
) -> None:
    """Test that assign resources calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(task_callback=task_callback)

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
    component_manager._submit_background_task = lambda task, task_callback: task(task_callback=task_callback)

    component_manager.release_all(task_callback=task_callback)

    api.release_resources.assert_called_once_with(task_callback=task_callback)
