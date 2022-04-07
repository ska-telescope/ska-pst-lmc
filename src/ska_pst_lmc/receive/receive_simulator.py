# -*- coding: utf-8 -*-
#
# This file is part of the PstReceive project
#
#
#
# Distributed under the terms of the BSD3 license.
# See LICENSE.txt for more info.

"""Module for providing the Simulated RECV capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from random import randint, random
from typing import List

from ska_pst_lmc.receive.receive_model import ReceiveData


def generate_random_update(nchan: int = 128) -> ReceiveData:
    """Generate a random update of ReceivedData.

    :param nchans: number of channels for relative weights.
    :type nchans: int
    :returns: a randomly generated receive data.
    """

    received_rate: float = 1.0 * randint(0, 90)
    received_data: int = int(received_rate * 1e9 / 8)
    dropped_rate: float = received_rate / 1000.0 * random()
    dropped_data: int = int(dropped_rate * 1e9 / 8)
    misordered_packets: int = randint(0, 3)
    malformed_packets: int = randint(0, 3)
    relative_weights: List[float] = nchan * [0.0]
    for i in range(nchan):
        relative_weights[i] = 1.0 * randint(0, 128)
    relative_weight = sum(relative_weights) / nchan

    return ReceiveData(
        received_data=received_data,
        received_rate=received_rate,
        dropped_data=dropped_data,
        dropped_rate=dropped_rate,
        misordeded_packets=misordered_packets,
        malformed_packets=malformed_packets,
        relative_weights=relative_weights,
        relative_weight=relative_weight,
    )


class PstReceiveSimulator:
    """Simulator for the RECV process of the PST.LMC sub-system.

    This is used to generate random data and simulate what happens during
    the RECV process. Current implementation has this internally with
    the TANGO device but future improvements will have this as a separate
    process and the TANGO will connect via an API.
    """

    # ----------
    # Attributes
    # ----------

    _received_data: int = 0
    _received_rate: float = 0.0
    _dropped_data: int = 0
    _dropped_rate: float = 0.0
    _nchan: int = 0
    _misordered_packets: int = 0
    _malformed_packets: int = 0
    _relative_weights: List[float] = []
    _relative_weight: float = 0.0

    def __init__(self: PstReceiveSimulator, *args: list, **kwargs: dict) -> None:
        """Initialise the simulator."""
        self._nchan = randint(128, 1024)
        self._relative_weights = [0] * self._nchan
        self._generate = False

    def start_scan(self):
        self._generate = True

    def stop_scan(self):
        self._generate = False

    def _update(self: PstReceiveSimulator) -> None:
        """Simulate the update of RECV data."""

        update: ReceiveData = generate_random_update(self._nchan)

        self._received_rate += update.received_rate
        self._received_data += update.received_data
        self._dropped_rate = update.dropped_rate
        self._dropped_data += update.dropped_data
        self._misordered_packets += update.misordeded_packets
        self._malformed_packets += update.malformed_packets
        self._relative_weights = update.relative_weights
        self._relative_weight = update.relative_weight

    def get_data(self) -> ReceiveData:
        """
        Get current RECV data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated RECV data.
        :rtype: :py:class:`ReceiveData`
        """
        if self._generate:
            self._update()

        return ReceiveData(
            received_data=self._received_data,
            received_rate=self._received_rate,
            dropped_data=self._dropped_data,
            dropped_rate=self._dropped_rate,
            misordeded_packets=self._misordered_packets,
            malformed_packets=self._malformed_packets,
            relative_weights=self._relative_weights,
            relative_weight=self._relative_weight,
        )
