# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains that the RECV simulator class."""


from typing import Any, Dict

import pytest

from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator


@pytest.fixture
def simulator() -> PstReceiveSimulator:
    """Create a simulator configuration."""
    return PstReceiveSimulator()


def test_get_data_will_update_data_when_scanning(
    simulator: PstReceiveSimulator,
    scan_request: Dict[str, Any],
) -> None:
    """Test to assert that simulator updates data."""
    simulator.start_scan(args=scan_request)

    empty: ReceiveData = ReceiveData()
    actual: ReceiveData = simulator.get_data()

    assert actual != empty


def test_get_data_wont_update_data_when_scanning_stops(
    simulator: PstReceiveSimulator,
    scan_request: Dict[str, Any],
) -> None:
    """Test to assert that simulator updates data."""
    simulator.start_scan(args=scan_request)

    empty: ReceiveData = ReceiveData()

    last_scan: ReceiveData = simulator.get_data()

    assert empty != last_scan

    simulator.stop_scan()
    actual: ReceiveData = simulator.get_data()

    assert actual == last_scan
