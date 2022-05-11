# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Simulated SMRB capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from random import randint
from typing import Any, Dict, List, Optional

from ska_pst_lmc.smrb.smrb_model import SharedMemoryRingBufferData


class PstSmrbSimulator:
    """Class used for simulating SMRB data."""

    _num_subbands: int
    _ring_buffer_size: int
    _ring_buffer_utilisation: float
    _subband_ring_buffer_sizes: List[int]
    _subband_ring_buffer_utilisations: List[float]

    def __init__(
        self: PstSmrbSimulator,
        num_subbands: Optional[int] = None,
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

        if subband_ring_buffer_sizes is not None:
            configuration["subband_ring_buffer_sizes"] = subband_ring_buffer_sizes

        self.configure(configuration=configuration)
        self._scan = False

    def configure(self: PstSmrbSimulator, configuration: dict) -> None:
        """
        Configure the simulator.

        Only the "num_subbands" parameter is used by this simulator
        and the "subband_ring_buffer_sizes" which should be a list
        the same length as the "num_subbands"

        :param configuration: the configuration to be configured
        :type configuration: dict

        :raises: AssertionError if length of subband sizes not the same as
            num_subbands.
        """
        if "num_subbands" in configuration:
            self._num_subbands = configuration["num_subbands"]
        else:
            self._num_subbands = randint(1, 4)

        if "subband_ring_buffer_sizes" in configuration:
            self._subband_ring_buffer_sizes = configuration["subband_ring_buffer_sizes"]
            assert (
                len(self._subband_ring_buffer_sizes) == self._num_subbands
            ), f"Expected length of subband_ring_buffer_sizes to be {self._num_subbands}"
        else:
            # simulate allocate of 2^22 to 2^28 bytes per subband
            self._subband_ring_buffer_sizes = [1048576 * randint(4, 64) for _ in range(self._num_subbands)]

        self._ring_buffer_size = sum(self._subband_ring_buffer_sizes)
        self._subband_ring_buffer_utilisations = self._num_subbands * [0.0]
        self._ring_buffer_utilisation = 0.0

    def deconfigure(self: PstSmrbSimulator) -> None:
        """Simulate deconfigure."""
        self._scan = False

    def scan(self: PstSmrbSimulator, args: dict) -> None:
        """Start scanning.

        :param: the scan arguments.
        """
        self._scan = True

    def end_scan(self: PstSmrbSimulator) -> None:
        """End scanning."""
        self._scan = False

    def abort(self: PstSmrbSimulator) -> None:
        """Tell the component to abort whatever it was doing."""
        self._scan = False

    def _update(self: PstSmrbSimulator) -> None:
        """Simulate the update of SMRB data."""
        for i in range(self._num_subbands):
            self._subband_ring_buffer_utilisations[i] = float(randint(0, 79))

        self._ring_buffer_utilisation = sum(
            [s * u for (s, u) in zip(self._subband_ring_buffer_sizes, self._subband_ring_buffer_utilisations)]
        )

    def get_data(self: PstSmrbSimulator) -> SharedMemoryRingBufferData:
        """
        Get current SMRB data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated SMRB data.
        :rtype: :py:class:`SharedMemoryRingBufferData`
        """
        if self._scan:
            self._update()

        return SharedMemoryRingBufferData(
            number_subbands=self._num_subbands,
            ring_buffer_size=self._ring_buffer_size,
            ring_buffer_utilisation=self._ring_buffer_utilisation,
            subband_ring_buffer_sizes=self._subband_ring_buffer_sizes,
            subband_ring_buffer_utilisations=self._subband_ring_buffer_utilisations,
        )
