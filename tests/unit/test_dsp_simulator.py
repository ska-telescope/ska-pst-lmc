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
        available_disk_space=800,
        subband_data_record_rates=[0.3, 0.1],
    )
    assert simulator.num_subbands == 2
    data = simulator.get_data()
    assert data.disk_capacity == 1000
    assert data.available_disk_space == 800
    assert data.disk_used_bytes == 200
    np.testing.assert_almost_equal(data.disk_used_percentage, 20.0)
    assert data.data_record_rate == 0.4
    np.testing.assert_almost_equal(data.available_recording_time, 2000.0, decimal=3)

    assert data.subband_data_record_rate[0] == 0.3
    assert data.subband_data_record_rate[1] == 0.1

    assert data.subband_data_recorded[0] == 0
    assert data.subband_data_recorded[1] == 0


def test_dps_simulator_configure_scan(simulator: PstDspSimulator) -> None:
    """Test that configuration of simulator sets up data."""
    import shutil

    configuration: Dict[str, Any] = {
        "num_subbands": 2,
    }

    simulator.configure_scan(configuration=configuration)

    assert simulator.num_subbands == 2

    data = simulator._data_store.monitor_data
    assert data.disk_capacity == shutil.disk_usage("/")[0]

    np.testing.assert_array_equal(simulator._subband_data_recorded, data.subband_data_recorded)
    np.testing.assert_array_equal(simulator._subband_data_record_rates, data.subband_data_record_rate)

    assert data.data_recorded == np.sum(simulator._subband_data_recorded)


def test_dsp_simulator_until_scan_get_data_returns_initial_data(
    simulator: PstDspSimulator,
    scan_request: Dict[str, Any],
) -> None:
    """Test that start_scan/stop_scan will only update data while scanning."""
    initial_data = simulator.get_data()

    next_data = simulator.get_data()

    assert initial_data == next_data

    simulator.start_scan(args=scan_request)
    prev_data = next_data = simulator.get_data()

    assert initial_data != next_data
    next_data = simulator.get_data()

    assert prev_data != next_data

    simulator.stop_scan()
    prev_data = next_data
    next_data = simulator.get_data()

    assert prev_data == next_data
