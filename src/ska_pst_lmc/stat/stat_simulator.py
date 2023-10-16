# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing the Simulated STAT capability."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from ska_pst_lmc.component import SUBBAND_1
from ska_pst_lmc.stat.stat_model import StatMonitorData, StatMonitorDataStore


class PstStatSimulator:
    """Class used for simulating STAT data."""

    _data_store: StatMonitorDataStore

    def __init__(
        self: PstStatSimulator,
    ) -> None:
        """Initialise the STAT simulator."""
        self._scan = False
        self._curr_data = StatMonitorData()
        self.configure_scan(configuration={})
        self._scan = False

    def configure_scan(self: PstStatSimulator, configuration: dict) -> None:
        """
        Simulate configuring a scan.

        :param configuration: the configuration to be configured
        :type configuration: dict
        :raises: AssertionError if length of subband sizes not the same as num_subbands.
        """
        self._data_store = StatMonitorDataStore()
        self._data_store.update_subband(
            subband_id=SUBBAND_1,
            subband_data=StatMonitorData(),
        )

    def deconfigure_scan(self: PstStatSimulator) -> None:
        """Simulate deconfiguring of a scan."""
        self._scan = False

    def start_scan(self: PstStatSimulator, args: dict) -> None:
        """
        Simulate start scanning.

        :param: the scan arguments.
        """
        self._scan = True

    def stop_scan(self: PstStatSimulator) -> None:
        """Simulate stop scanning."""
        self._scan = False

    def abort(self: PstStatSimulator) -> None:
        """Tell the component to abort whatever it was doing."""
        self._scan = False

    def _update(self: PstStatSimulator) -> None:
        """Simulate the update of STAT data."""

        def _gen_stats() -> Tuple[float, float, int]:
            data = np.random.randn(1024).astype(dtype=np.float32)
            clipped_samples = np.abs(data) >= 3.0
            num_clipped_samples = np.count_nonzero(clipped_samples)
            data[clipped_samples] = 3.0 * np.sign(data[clipped_samples])

            mean = np.mean(data, dtype=np.float32)
            variance = np.var(data, ddof=1, dtype=np.float32)

            return (mean, variance, num_clipped_samples)

        data = {}
        for dim in ["real", "imag"]:
            for pol in ["pol_a", "pol_b"]:
                for suffix in ["", "_masked"]:
                    mean_key = f"{dim}_{pol}_mean_freq_avg{suffix}"
                    variance_key = f"{dim}_{pol}_variance_freq_avg{suffix}"
                    num_clipped_samples_key = f"{dim}_{pol}_num_clipped_samples{suffix}"

                    (mean, variance, num_clipped_samples) = _gen_stats()
                    data[mean_key] = mean
                    data[variance_key] = variance
                    data[num_clipped_samples_key] = num_clipped_samples

        self._data_store.update_subband(
            subband_id=SUBBAND_1,
            subband_data=StatMonitorData(**data),
        )

    def get_data(self: PstStatSimulator) -> StatMonitorData:
        """
        Get current STAT data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated STAT data.
        :rtype: :py:class:`StatMonitorData`
        """
        if self._scan:
            self._update()

        return self._data_store.monitor_data

    def get_subband_data(self: PstStatSimulator) -> Dict[int, StatMonitorData]:
        """Get simulated subband data."""
        if self._scan:
            self._update()

        return self._data_store._subband_data
