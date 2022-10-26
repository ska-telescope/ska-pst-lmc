# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Simulated DSP capability for PST."""

from __future__ import annotations

from random import randint, random
from typing import Any, Dict, List, Optional

import numpy as np

from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorData, DspDiskMonitorDataStore, DspDiskSubbandMonitorData

__all__ = ["PstDspSimulator"]


class PstDspSimulator:
    """Simulator for the DSP process of the PST.LMC sub-system.

    This is used to generate random data and simulate what for the DSP
    subsystem. This simulator is used for all the subbands. For the
    LMC state model most methods are no-op operations but when a scan
    is in process the :py:meth:`get_data` method will randomly update
    the monitoring data.

    For DSP.DSK functionality the following properties can be set:
    * Total disk size
    * Availabe disk size
    * Subband write rates
    * Subband bytes written

    To be able to simulate situation where the disk is near full, or is
    full, the method :py:meth:`simulate_disk_capacity` should be called
    to override the current value.
    """

    _data_store: DspDiskMonitorDataStore

    def __init__(
        self: PstDspSimulator,
        num_subbands: Optional[int] = None,
        disk_capacity: Optional[int] = None,
        subband_write_rates: Optional[List[float]] = None,
        subband_bytes_written: Optional[List[int]] = None,
    ) -> None:
        """Initialise the DSP simulator.

        :param num_subbands: number of subbands, if None a random number is used.
        :type num_subbands: int
        :param disk_capacity: the max size of the size to simulate, default is
            1_000_000_000_000 bytes.
        :type disk_capacity: int
        :param disk_available_bytes: initial available space on disk to simulate, default is
            1_000_000_000_000 bytes.
        :type disk_available_bytes: int
        :param subband_write_rates: the write rates per subband. Default is a random array.
        :type subband_write_rates: List[float]
        :param subband_bytes_written: initial bytes written to disk. Default is a list of zeros.
        :type subband_bytes_written: List[int]
        """
        configuration: Dict[str, Any] = {}
        if num_subbands is not None:
            configuration["num_subbands"] = num_subbands

        if disk_capacity is not None:
            configuration["disk_capacity"] = disk_capacity

        if subband_write_rates is not None:
            configuration["subband_write_rates"] = subband_write_rates

        if subband_bytes_written is not None:
            configuration["subband_bytes_written"] = subband_bytes_written

        self.configure_scan(configuration=configuration)
        self._scan = False

    @property
    def disk_capacity(self: PstDspSimulator) -> int:
        """Get simulated disk capacity."""
        return self._disk_capacity

    @disk_capacity.setter
    def disk_capacity(self: PstDspSimulator, disk_capacity: int) -> None:
        """Set simulated disk capacity.

        :param disk_capacity: the new disk capacity, in bytes.
        """
        self._disk_capacity = disk_capacity

    @property
    def disk_available_bytes(self: PstDspSimulator) -> int:
        """Get simulated available bytes left of disk."""
        return self._disk_available_bytes

    @disk_available_bytes.setter
    def disk_available_bytes(self: PstDspSimulator, disk_available_bytes: int) -> None:
        """Set simulated available bytes left of disk.

        :param disk_available_bytes: the new about of bytes available on the disk.
        """
        self._disk_available_bytes = disk_available_bytes

    def configure_scan(self: PstDspSimulator, configuration: dict) -> None:
        """
        Simulate configuring a scan.

        Only the "num_subbands" parameter is used by this simulator.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        if "num_subbands" in configuration:
            self.num_subbands = configuration["num_subbands"]
        else:
            self.num_subbands = randint(1, 4)

        self.disk_capacity = disk_capacity = configuration.get("disk_capacity", 1_000_000_000_000)

        self._subband_write_rates = configuration.get(
            "subband_write_rates", self.num_subbands * [1e9 * (random() + 0.5)]
        )

        self._subband_bytes_written = subband_bytes_written = configuration.get(
            "subband_bytes_written", self.num_subbands * [int(1e9 * (random() + 0.5))]
        )

        self.disk_available_bytes = max(0, int(disk_capacity - np.sum(subband_bytes_written)))

        assert len(self._subband_write_rates) == self.num_subbands
        assert len(self._subband_bytes_written) == self.num_subbands

        self._data_store = DspDiskMonitorDataStore()
        for idx in range(self.num_subbands):
            self._data_store.update_subband(
                subband_id=(idx + 1),
                subband_data=DspDiskSubbandMonitorData(
                    disk_capacity=self.disk_capacity,
                    disk_available_bytes=self.disk_available_bytes,
                    bytes_written=self._subband_bytes_written[idx],
                    write_rate=self._subband_write_rates[idx],
                ),
            )

    def deconfigure_scan(self: PstDspSimulator) -> None:
        """Simulate deconfiguring of a scan."""
        self._scan = False

    def start_scan(self: PstDspSimulator, args: dict) -> None:
        """Simulate start scanning.

        :param: the scan arguments.
        """
        self._scan = True

    def stop_scan(self: PstDspSimulator) -> None:
        """Simulate stop scanning."""
        self._scan = False

    def abort(self: PstDspSimulator) -> None:
        """Tell the component to abort whatever it was doing."""
        self._scan = False

    def _update(self: PstDspSimulator) -> None:
        """Simulate the update of DSP data."""
        for idx in range(self.num_subbands):
            # create initial write rate
            write_rate = self._subband_write_rates[idx]

            # determine actual bytes written, can't go more than disk available
            bytes_written = int(write_rate)
            bytes_written = min(bytes_written, self.disk_available_bytes)

            # update disk available
            self.disk_available_bytes -= bytes_written

            # update subband values
            self._subband_bytes_written[idx] += bytes_written

            self._data_store.update_subband(
                subband_id=(idx + 1),
                subband_data=DspDiskSubbandMonitorData(
                    disk_capacity=self.disk_capacity,
                    disk_available_bytes=self.disk_available_bytes,
                    bytes_written=self._subband_bytes_written[idx],
                    write_rate=self._subband_write_rates[idx],
                ),
            )

    def get_data(self: PstDspSimulator) -> DspDiskMonitorData:
        """
        Get current DSP data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated DSP data.
        :rtype: :py:class:`DspDiskMonitorData`
        """
        if self._scan:
            self._update()

        return self._data_store.monitor_data

    def get_subband_data(self: PstDspSimulator) -> Dict[int, DspDiskSubbandMonitorData]:
        """Get simulated subband data."""
        if self._scan:
            self._update()

        return self._data_store._subband_data
