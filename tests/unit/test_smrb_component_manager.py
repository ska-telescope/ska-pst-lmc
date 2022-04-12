# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV component managers class."""

import logging
from unittest.mock import MagicMock

import pytest
from ska_tango_base.control_model import SimulationMode

from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager


@pytest.fixture
def component_manager(
    simulation_mode: SimulationMode,
    logger: logging.Logger,
) -> PstReceiveComponentManager:
    """Create instance of a component manager."""
    return PstReceiveComponentManager(
        simulation_mode=simulation_mode,
        logger=logger,
        communication_state_callback=MagicMock(),
        component_state_callback=MagicMock(),
    )


@pytest.fixture
def simulation_mode(request: pytest.FixtureRequest) -> SimulationMode:
    """Set simulation mode for test."""
    try:
        return request.param.get("simulation_mode", SimulationMode.TRUE)  # type: ignore
    except Exception:
        return SimulationMode.TRUE


def test_start_communicating_calls_connect_on_api(component_manager: PstReceiveComponentManager) -> None:
    """Assert start/stop communicating calls API."""
    api = MagicMock()
    component_manager._api = api

    component_manager.start_communicating()
    api.connect.assert_called_once()
    api.disconnect.assert_not_called()

    component_manager.stop_communicating()
    api.disconnect.assert_called_once()
