# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the SMRB simulator class."""


from typing import Any, Dict

import pytest

from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator


@pytest.fixture
def simulator() -> PstSmrbSimulator:
    """Create a SMRB Simulator fixture."""
    return PstSmrbSimulator()


def test_configure_of_simulator(simulator: PstSmrbSimulator) -> None:
    """Test that configuration of simulator sets up data."""
    configuration: Dict[str, Any] = {"num_subbands": 2, "subband_ring_buffer_sizes": [42, 1138]}

    simulator.configure(configuration=configuration)

    assert simulator._num_subbands == 2
    assert simulator._ring_buffer_size == 1180
    assert simulator._ring_buffer_utilisation == 0.0
    assert simulator._subband_ring_buffer_utilisations == [0.0, 0.0]
    assert simulator._subband_ring_buffer_sizes == [42, 1138]


def test_configure_throws_assertion_on_difference_in_num_subbands_and_buffer_sizes(
    simulator: PstSmrbSimulator,
) -> None:
    """Test that configuration will throw an assertion error on invalid configuration."""
    configuration: Dict[str, Any] = {"num_subbands": 4, "subband_ring_buffer_sizes": [1024]}

    with pytest.raises(AssertionError) as e_info:
        simulator.configure(configuration=configuration)

    assert "Expected length of subband_ring_buffer_sizes to be 4" == str(e_info.value)


def test_configure_handles_no_subbands_configuration(simulator: PstSmrbSimulator) -> None:
    """Test default configuration without num_subbands still initialises simulator."""
    simulator.configure(configuration={})

    num_subbands: int = simulator._num_subbands
    assert num_subbands in [1, 2, 3, 4]
    assert simulator._ring_buffer_utilisation == 0.0
    assert simulator._subband_ring_buffer_utilisations == num_subbands * [0.0]
    assert len(simulator._subband_ring_buffer_sizes) == num_subbands
    assert simulator._ring_buffer_size == sum(simulator._subband_ring_buffer_sizes)


def test_until_scan_get_data_returns_initial_data(simulator: PstSmrbSimulator) -> None:
    """Test that scan/end_scan will only update data while scanning."""
    initial_data = simulator.get_data()

    next_data = simulator.get_data()

    assert initial_data == next_data

    simulator.scan(args={})
    prev_data = next_data = simulator.get_data()

    assert initial_data != next_data
    next_data = simulator.get_data()

    assert prev_data != next_data

    simulator.end_scan()
    prev_data = next_data
    next_data = simulator.get_data()

    assert prev_data == next_data
