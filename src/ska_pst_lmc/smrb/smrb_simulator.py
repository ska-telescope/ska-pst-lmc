# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Simulated SMRB capability."""

from __future__ import annotations

from random import randint
from typing import Any, Dict, List, Optional

from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData, SmrbMonitorDataStore, SmrbSubbandMonitorData


class PstSmrbSimulator:
    """Class used for simulating SMRB data."""

    _data_store: SmrbMonitorDataStore

    def __init__(
        self: PstSmrbSimulator,
        num_subbands: Optional[int] = None,
        subband_num_of_buffers: Optional[List[int]] = None,
        subband_ring_buffer_sizes: Optional[List[int]] = None,
    ) -> None:
        """Initialise the SMRB simulator.

        :param num_subbands: number of subbands, if None a random number is used.
        :type num_subbands: int
        :param subband_ring_buffer_sizes: list of sizes of subbands
        :type subband_ring_buffer_sizes: list of ints

        :raises: AssertionError if length of subband sizes not the same as
            num_subbands.
        """
        configuration: Dict[str, Any] = {}
        if num_subbands is not None:
            configuration["num_subbands"] = num_subbands

        if subband_num_of_buffers is not None:
            configuration["subband_num_of_buffers"] = subband_num_of_buffers

        if subband_ring_buffer_sizes is not None:
            configuration["subband_ring_buffer_sizes"] = subband_ring_buffer_sizes

        self.configure_scan(configuration=configuration)
        self._scan = False

    def configure_scan(self: PstSmrbSimulator, configuration: dict) -> None:
        """
        Simulate configuring a scan.

        Only the "num_subbands" parameter is used by this simulator
        and the "subband_ring_buffer_sizes" which should be a list
        the same length as the "num_subbands"

        :param configuration: the configuration to be configured
        :type configuration: dict

        :raises: AssertionError if length of subband sizes not the same as
            num_subbands.
        """
        if "num_subbands" in configuration:
            self.num_subbands = configuration["num_subbands"]
        else:
            self.num_subbands = randint(1, 4)

        # set up subband ring buffer sizes
        subband_ring_buffer_sizes = configuration.get(
            "subband_ring_buffer_sizes", [1048576 * randint(4, 64) for _ in range(self.num_subbands)]
        )
        assert (
            len(subband_ring_buffer_sizes) == self.num_subbands
        ), f"Expected length of subband_ring_buffer_sizes to be { self.num_subbands}"

        subband_num_of_buffers = configuration.get(
            "subband_num_of_buffers", [randint(4, 8) for _ in range(self.num_subbands)]
        )
        assert (
            len(subband_num_of_buffers) == self.num_subbands
        ), f"Expected length of subband_num_of_buffers to be { self.num_subbands}"

        self._data_store = SmrbMonitorDataStore()
        for idx in range(self.num_subbands):
            num_of_buffers = subband_num_of_buffers[idx]
            buffer_size = subband_ring_buffer_sizes[idx]

            self._data_store.update_subband(
                subband_id=(idx + 1),
                subband_data=SmrbSubbandMonitorData(
                    buffer_size=buffer_size,
                    num_of_buffers=num_of_buffers,
                ),
            )

    def deconfigure_scan(self: PstSmrbSimulator) -> None:
        """Simulate deconfiguring of a scan."""
        self._scan = False

    def start_scan(self: PstSmrbSimulator, args: dict) -> None:
        """Simulate start scanning.

        :param: the scan arguments.
        """
        self._scan = True

    def stop_scan(self: PstSmrbSimulator) -> None:
        """Simulate stop scanning."""
        self._scan = False

    def abort(self: PstSmrbSimulator) -> None:
        """Tell the component to abort whatever it was doing."""
        self._scan = False

    def _update(self: PstSmrbSimulator) -> None:
        """Simulate the update of SMRB data."""
        for idx in range(self.num_subbands):
            subband_data = self._data_store._subband_data[idx + 1]

            written = randint(2**10, 2**16)
            # between 0-70% - too high and it causes Tango k8s-tests to fail
            utilisation = randint(0, 700) / 10.0
            full = int(subband_data.num_of_buffers * utilisation / 100.0)

            subband_data.total_written += written
            subband_data.total_read += written
            subband_data.full = full

    def get_data(self: PstSmrbSimulator) -> SmrbMonitorData:
        """
        Get current SMRB data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated SMRB data.
        :rtype: :py:class:`SmrbMonitorData`
        """
        if self._scan:
            self._update()

        return self._data_store.monitor_data

    def get_subband_data(self: PstSmrbSimulator) -> Dict[int, SmrbSubbandMonitorData]:
        """Get simulated subband data."""
        if self._scan:
            self._update()

        return self._data_store._subband_data

    def set_log_level(self: PstSmrbSimulator) -> None:
        """Set SMRB LogLevel"""
