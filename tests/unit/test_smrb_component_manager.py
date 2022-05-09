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

from ska_pst_lmc.smrb.smrb_component_manager import PstSmrbComponentManager
from ska_pst_lmc.smrb.smrb_model import SharedMemoryRingBufferData
from ska_pst_lmc.smrb.smrb_process_api import PstSmrbProcessApi, PstSmrbProcessApiSimulator


@pytest.fixture
def component_manager(
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstSmrbProcessApi,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
) -> PstSmrbComponentManager:
    """Create instance of a component manager."""
    return PstSmrbComponentManager(
        simulation_mode=simulation_mode,
        logger=logger,
        communication_state_callback=communication_state_callback,
        component_state_callback=component_state_callback,
        api=api,
    )


@pytest.fixture
def api(
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
        raise ValueError("Expected simulation mode to be true")


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
    "property",
    [
        ("ring_buffer_utilisation"),
        ("ring_buffer_size"),
        ("number_subbands"),
        ("subband_ring_buffer_utilisations"),
        ("subband_ring_buffer_sizes"),
    ],
)
def test_properties_come_from_api_monitor_data(
    component_manager: PstSmrbComponentManager,
    api: PstSmrbProcessApi,
    monitor_data: SharedMemoryRingBufferData,
    property: str,
) -> None:
    """Test properties are coming from API monitor data."""
    api = MagicMock()
    type(api).monitor_data = monitor_data
    component_manager._api = api

    actual = getattr(component_manager, property)
    expected = getattr(monitor_data, property)

    assert actual == expected
