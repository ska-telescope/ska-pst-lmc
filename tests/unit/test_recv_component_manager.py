# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV component managers class."""

import logging
import time
import unittest
from typing import Optional
from unittest.mock import MagicMock

import pytest
from ska_tango_base.control_model import SimulationMode

from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator
from ska_pst_lmc.util.background_task import BackgroundTask

root_logger: logging.Logger = logging.getLogger()


def component_manager_fixture(
    simulation_mode: SimulationMode = SimulationMode.TRUE,
    logger: Optional[logging.Logger] = None,
) -> PstReceiveComponentManager:
    """Create instance of a component manager."""
    return PstReceiveComponentManager(
        simulation_mode=simulation_mode,
        logger=logger or root_logger,
        communication_state_callback=MagicMock(),
        component_state_callback=MagicMock(),
    )


def test_start_communicating_when_in_simulation_mode() -> None:
    """Assert start communicating starts a background task."""
    component_manager = component_manager_fixture()

    assert component_manager._communication_task is None
    assert component_manager._simulator is not None

    component_manager.start_communicating()

    assert component_manager._communication_task is not None
    assert component_manager._communication_task.running()


def test_start_communicating_call_monitor() -> None:
    """Assert the background task used is the monitor method."""
    component_manager = component_manager_fixture()
    component_manager._monitor_action = MagicMock(name="_monitor_task")  # type: ignore

    component_manager._monitor_action.assert_not_called()

    component_manager.start_communicating()
    time.sleep(0.01)
    component_manager._monitor_action.assert_called()


def test_monitor_function_gets_values_from_simulator() -> None:
    """Assert that the compoment manager values updated from monitor action."""
    component_manager = component_manager_fixture()
    simulator: PstReceiveSimulator = component_manager._simulator
    assert simulator is not None

    with unittest.mock.patch.object(simulator, "get_data", wraps=simulator.get_data) as get_data:
        assert component_manager.received_data == 0
        assert component_manager.received_rate == 0.0
        assert component_manager.dropped_data == 0
        assert component_manager.dropped_rate == 0.0
        assert component_manager.malformed_packets == 0
        assert component_manager.misordered_packets == 0
        assert component_manager.relative_weight == 0.0
        assert len(component_manager.relative_weights) == 0

        component_manager._monitor_action()
        get_data.assert_called_once()

        assert component_manager.received_data == simulator._received_data
        assert component_manager.received_rate == simulator._received_rate
        assert component_manager.dropped_data == simulator._dropped_data
        assert component_manager.dropped_rate == simulator._dropped_rate
        assert component_manager.malformed_packets == simulator._malformed_packets
        assert component_manager.misordered_packets == simulator._misordered_packets
        assert component_manager.relative_weight == simulator._relative_weight
        assert component_manager.relative_weights == simulator._relative_weights


def test_start_communicating_when_not_in_simulation_mode() -> None:
    """Assert start communication throws NotImplementError for non-simulation mode."""
    component_manager = component_manager_fixture(simulation_mode=SimulationMode.FALSE)
    with pytest.raises(NotImplementedError):
        component_manager.start_communicating()


def test_stop_communicating_stops_stops_background_task() -> None:
    """Assert stop communicating calls stop on background task."""
    component_manager = component_manager_fixture()

    assert component_manager._communication_task is None
    assert component_manager._simulator is not None

    component_manager.start_communicating()
    time.sleep(0.01)
    assert component_manager._communication_task and component_manager._communication_task.running()

    component_manager.stop_communicating()
    time.sleep(0.01)
    assert not component_manager._communication_task.running()


def test_del_calls_stops_background_task() -> None:
    """Test that the deconstructor of component manager stops task."""
    component_manager = component_manager_fixture()

    component_manager.start_communicating()
    time.sleep(0.01)

    task: Optional[BackgroundTask] = component_manager._communication_task
    assert task is not None
    assert task.running()

    component_manager.__del__()
    while task.running():
        time.sleep(0.05)
