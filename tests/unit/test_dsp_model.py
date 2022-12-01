# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the DSP API."""

from __future__ import annotations

import sys

from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorDataStore, DspDiskSubbandMonitorData


def test_dsp_disk_monitor_data_store() -> None:
    """Test DSP disk monitor data store."""
    import shutil

    data_store = DspDiskMonitorDataStore()

    monitor_data = data_store.monitor_data

    assert monitor_data.available_disk_space == sys.maxsize
    assert monitor_data.disk_capacity == sys.maxsize

    (disk_capacity, _, available_disk_space) = shutil.disk_usage("/")

    data_store.update_disk_stats(disk_capacity=disk_capacity, available_disk_space=available_disk_space)
    updated_monitor_data = data_store.monitor_data

    assert updated_monitor_data.disk_capacity == disk_capacity
    assert updated_monitor_data.available_disk_space == available_disk_space

    subband_data = DspDiskSubbandMonitorData(
        available_disk_space=available_disk_space - 2,
        disk_capacity=disk_capacity,
        data_recorded=2,
        data_record_rate=0.1,
    )

    data_store.update_subband(1, subband_data=subband_data)

    assert data_store.monitor_data.available_disk_space == (available_disk_space - 2)
    assert data_store.monitor_data.disk_capacity == disk_capacity
