# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains that the STAT simulator class."""


from typing import Any, Dict

import pytest

from ska_pst_lmc.stat.stat_model import StatMonitorData
from ska_pst_lmc.stat.stat_simulator import PstStatSimulator


@pytest.fixture
def simulator() -> PstStatSimulator:
    """Create a simulator configuration."""
    return PstStatSimulator()


def test_get_data_will_update_data_when_scanning(
    simulator: PstStatSimulator,
    scan_request: Dict[str, Any],
) -> None:
    """Test to assert that simulator updates data."""
    simulator.start_scan(args=scan_request)

    empty: StatMonitorData = StatMonitorData()
    actual: StatMonitorData = simulator.get_data()

    assert actual != empty


def test_get_data_wont_update_data_when_scanning_stops(
    simulator: PstStatSimulator,
    scan_request: Dict[str, Any],
) -> None:
    """Test to assert that simulator updates data."""
    simulator.start_scan(args=scan_request)

    empty: StatMonitorData = StatMonitorData()

    last_scan: StatMonitorData = simulator.get_data()

    assert empty != last_scan

    simulator.stop_scan()
    actual: StatMonitorData = simulator.get_data()

    assert actual == last_scan
