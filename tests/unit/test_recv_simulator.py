# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains that the RECV simulator class."""


import pytest

from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator


@pytest.fixture
def simulator() -> PstReceiveSimulator:
    """Create a simulator configuration."""
    return PstReceiveSimulator()


def test_default_values(simulator: PstReceiveSimulator) -> None:
    """Test to see if that the simulator is initialised with defaults."""
    assert simulator._received_data == 0
    assert simulator._received_rate == 0.0
    assert simulator._dropped_data == 0.0
    assert simulator._dropped_rate == 0.0
    assert simulator._nchan >= 128
    assert simulator._misordered_packets == 0


def test_get_data_will_update_data_when_scanning(
    simulator: PstReceiveSimulator,
    scan_request: dict,
) -> None:
    """Test to assert that simulator updates data."""
    simulator.scan(args=scan_request)

    empty: ReceiveData = ReceiveData()
    actual: ReceiveData = simulator.get_data()

    assert actual != empty


def test_get_data_wont_update_data_when_scanning_stops(
    simulator: PstReceiveSimulator,
    scan_request: dict,
) -> None:
    """Test to assert that simulator updates data."""
    simulator.scan(args=scan_request)

    empty: ReceiveData = ReceiveData()

    last_scan: ReceiveData = simulator.get_data()

    assert empty != last_scan

    simulator.end_scan()
    actual: ReceiveData = simulator.get_data()

    assert actual == last_scan
