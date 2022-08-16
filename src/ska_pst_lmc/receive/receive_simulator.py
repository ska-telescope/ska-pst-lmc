# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Simulated RECV capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from random import randint, random

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

    return ReceiveData(
        received_data=received_data,
        received_rate=received_rate,
        dropped_data=dropped_data,
        dropped_rate=dropped_rate,
        misordered_packets=misordered_packets,
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

    def __init__(self: PstReceiveSimulator, *args: list, **kwargs: dict) -> None:
        """Initialise the simulator."""
        self._nchan = randint(128, 1024)
        self._scan = False

    def configure(self: PstReceiveSimulator, configuration: dict) -> None:
        """
        Configure the simulator.

        Only the "nchan" parameter is used by this simulator.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        if "nchan" in configuration:
            self._nchan = configuration["nchan"]
        else:
            self._nchan = randint(128, 1024)

    def deconfigure(self: PstReceiveSimulator) -> None:
        """Simulate deconfigure."""
        self._scan = False

    def scan(self: PstReceiveSimulator, args: dict) -> None:
        """Start scanning.

        :param: the scan arguments.
        """
        self._scan = True

    def end_scan(self: PstReceiveSimulator) -> None:
        """End scanning."""
        self._scan = False

    def abort(self: PstReceiveSimulator) -> None:
        """Tell the component to abort whatever it was doing."""
        self._scan = False

    def _update(self: PstReceiveSimulator) -> None:
        """Simulate the update of RECV data."""
        update: ReceiveData = generate_random_update(self._nchan)

        self._received_rate += update.received_rate
        self._received_data += update.received_data
        self._dropped_rate = update.dropped_rate
        self._dropped_data += update.dropped_data
        self._misordered_packets += update.misordered_packets

    def get_data(self: PstReceiveSimulator) -> ReceiveData:
        """
        Get current RECV data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated RECV data.
        :rtype: :py:class:`ReceiveData`
        """
        if self._scan:
            self._update()

        return ReceiveData(
            received_data=self._received_data,
            received_rate=self._received_rate,
            dropped_data=self._dropped_data,
            dropped_rate=self._dropped_rate,
            misordered_packets=self._misordered_packets,
        )
