# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains that the RECV simulator class."""

from typing import List

from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator


def __create_expected_relative_weights(nchans: int) -> List[float]:
    weights: List[float] = [0.0] * nchans
    assert len(weights) == nchans
    return weights


def test_default_values() -> None:
    """Test to see if that the simulator is initialised with defaults."""
    simulator = PstReceiveSimulator()
    assert simulator._received_data == 0
    assert simulator._received_rate == 0.0
    assert simulator._dropped_data == 0.0
    assert simulator._dropped_rate == 0.0
    assert simulator._nchan >= 128
    assert simulator._misordered_packets == 0
    assert simulator._malformed_packets == 0
    assert simulator._relative_weight == 0.0

    expected: List[float] = __create_expected_relative_weights(simulator._nchan)
    assert expected == simulator._relative_weights


def test_get_data_will_update_data_when_scanning() -> None:
    """Test to assert that simulator updates data."""
    simulator = PstReceiveSimulator()
    simulator.scan(args={})

    empty: ReceiveData = ReceiveData(
        received_data=0,
        received_rate=0.0,
        dropped_data=0,
        dropped_rate=0.0,
        misordered_packets=0,
        malformed_packets=0,
        relative_weight=0.0,
        relative_weights=__create_expected_relative_weights(simulator._nchan),
    )
    actual: ReceiveData = simulator.get_data()

    assert actual != empty


def test_get_data_wont_update_data_when_scanning_stops() -> None:
    """Test to assert that simulator updates data."""
    simulator = PstReceiveSimulator()
    simulator.scan(args={})

    empty: ReceiveData = ReceiveData(
        received_data=0,
        received_rate=0.0,
        dropped_data=0,
        dropped_rate=0.0,
        misordered_packets=0,
        malformed_packets=0,
        relative_weight=0.0,
        relative_weights=__create_expected_relative_weights(simulator._nchan),
    )

    last_scan: ReceiveData = simulator.get_data()

    assert empty != last_scan

    simulator.end_scan()
    actual: ReceiveData = simulator.get_data()

    assert actual == last_scan
