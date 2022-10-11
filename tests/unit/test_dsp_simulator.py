# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the DSP simulator class."""


from typing import Any, Dict

import numpy as np
import pytest

from ska_pst_lmc.dsp.dsp_simulator import PstDspSimulator


@pytest.fixture
def simulator() -> PstDspSimulator:
    """Create a DSP Simulator fixture."""
    return PstDspSimulator()


def test_dsp_simulator_using_constructor() -> None:
    """Test constructor creates correct simulator config."""
    simulator = PstDspSimulator(
        num_subbands=2,
        disk_capacity=1000,
        subband_bytes_written=[150, 50],
        subband_write_rates=[0.3, 0.1],
    )
    assert simulator.num_subbands == 2
    data = simulator.get_data()
    assert data.disk_capacity == 1000
    assert data.disk_available_bytes == 800
    assert data.disk_used_bytes == 200
    np.testing.assert_almost_equal(data.disk_used_percentage, 20.0)
    assert data.write_rate == 0.4
    np.testing.assert_almost_equal(data.available_recording_time, 2000.0, decimal=3)

    assert data.subband_write_rate[0] == 0.3
    assert data.subband_write_rate[1] == 0.1

    assert data.subband_bytes_written[0] == 150
    assert data.subband_bytes_written[1] == 50


def test_dps_simulator_configure(simulator: PstDspSimulator) -> None:
    """Test that configuration of simulator sets up data."""
    configuration: Dict[str, Any] = {
        "num_subbands": 2,
    }

    simulator.configure(configuration=configuration)

    assert simulator.num_subbands == 2

    data = simulator._data_store.monitor_data
    assert data.disk_capacity == 1_000_000_000_000

    np.testing.assert_array_equal(simulator._subband_bytes_written, data.subband_bytes_written)
    np.testing.assert_array_equal(simulator._subband_write_rates, data.subband_write_rate)

    assert data.bytes_written == np.sum(simulator._subband_bytes_written)


def test_dsp_simulator_until_scan_get_data_returns_initial_data(
    simulator: PstDspSimulator,
    scan_request: dict,
) -> None:
    """Test that scan/end_scan will only update data while scanning."""
    initial_data = simulator.get_data()

    next_data = simulator.get_data()

    assert initial_data == next_data

    simulator.scan(args=scan_request)
    prev_data = next_data = simulator.get_data()

    assert initial_data != next_data
    next_data = simulator.get_data()

    assert prev_data != next_data

    simulator.end_scan()
    prev_data = next_data
    next_data = simulator.get_data()

    assert prev_data == next_data
