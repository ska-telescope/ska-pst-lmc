# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the SMRB model classes."""

from random import randint

import numpy as np

from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData, SmrbMonitorDataStore, SubbandMonitorData


def generate_smrb_subband_monitor_data() -> SubbandMonitorData:
    """Create random SMRB subband data."""
    buffer_size = randint(100, 1000)
    num_of_buffers = randint(100, 1000)
    total_written = randint(1, 1_000_000)
    total_read = total_written - 1
    full = randint(1, num_of_buffers)

    return SubbandMonitorData(
        buffer_size=buffer_size,
        num_of_buffers=num_of_buffers,
        total_written=total_written,
        total_read=total_read,
        full=full,
    )


def test_smrb_subband_monitor_data() -> None:
    """Test properties of subband data."""
    data = generate_smrb_subband_monitor_data()

    full = data.full
    num_of_buffers = data.num_of_buffers
    buffer_size = data.buffer_size

    expected_utilisation = full / num_of_buffers * 100.0

    assert abs(data.utilisation - expected_utilisation) < 0.01

    expected_utilised_bytes = full / num_of_buffers * buffer_size
    assert data.utilised_bytes == expected_utilised_bytes


def test_smrb_data_store_with_one_subband() -> None:
    """Test getting monitor data when there is one subband."""
    data_store = SmrbMonitorDataStore()
    subband_data = generate_smrb_subband_monitor_data()

    data_store.subband_data[1] = subband_data

    actual: SmrbMonitorData = data_store.get_smrb_monitor_data()

    assert actual.number_subbands == 1
    assert actual.ring_buffer_read == subband_data.total_read
    assert actual.ring_buffer_written == subband_data.total_written
    assert actual.ring_buffer_size == subband_data.buffer_size
    assert abs(actual.ring_buffer_utilisation - subband_data.utilisation) < 0.01


def test_smrb_data_store_with_multiple_subbands() -> None:
    """Test getting monitor data when there is one subband."""
    num_subbands = randint(2, 4)
    data_store = SmrbMonitorDataStore()

    total_read = 0
    total_written = 0
    total_buffer_size = 0
    total_full_bytes = 0.0

    expected_subband_read = num_subbands * [0]
    expected_subband_written = num_subbands * [0]
    expected_subband_buffer_sizes = num_subbands * [0]
    expected_subband_utilisations = num_subbands * [0.0]

    for idx in range(num_subbands):
        subband_data = generate_smrb_subband_monitor_data()
        data_store.subband_data[idx + 1] = subband_data

        total_read += subband_data.total_read
        total_written += subband_data.total_written
        total_buffer_size += subband_data.buffer_size
        total_full_bytes += subband_data.utilised_bytes

        expected_subband_read[idx] = subband_data.total_read
        expected_subband_written[idx] = subband_data.total_written
        expected_subband_buffer_sizes[idx] = subband_data.buffer_size
        expected_subband_utilisations[idx] = subband_data.utilisation

    actual: SmrbMonitorData = data_store.get_smrb_monitor_data()

    assert actual.number_subbands == num_subbands
    assert actual.ring_buffer_read == total_read
    assert actual.ring_buffer_written == total_written
    assert actual.ring_buffer_size == total_buffer_size

    expected_utilisation = total_full_bytes / total_buffer_size * 100.0

    assert abs(actual.ring_buffer_utilisation - expected_utilisation) < 0.01
    assert actual.subband_ring_buffer_read == expected_subband_read
    assert actual.subband_ring_buffer_written == expected_subband_written
    assert actual.subband_ring_buffer_sizes == expected_subband_buffer_sizes

    np.testing.assert_allclose(actual.subband_ring_buffer_utilisations, expected_subband_utilisations)
