# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Simulated RECV capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from random import randint, random
from typing import Any, Dict, Optional

from ska_pst_lmc.receive.receive_model import ReceiveData


def generate_random_update() -> ReceiveData:
    """Generate a random update of ReceivedData."""
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

    _subband_data: Dict[int, ReceiveData]

    def __init__(self: PstReceiveSimulator, num_subbands: Optional[int] = None, **kwargs: Any) -> None:
        """Initialise the simulator."""
        configuration: Dict[str, Any] = {}
        if num_subbands is not None:
            configuration["num_subbands"] = num_subbands

        self.configure_scan(configuration=configuration)
        self._scan = False

    def configure_scan(self: PstReceiveSimulator, configuration: dict) -> None:
        """
        Simulate configuring a scan.

        Only the "nchan" parameter is used by this simulator.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        if "num_subbands" in configuration:
            self.num_subbands = configuration["num_subbands"]
        else:
            self.num_subbands = randint(1, 4)

        self._subband_data = {subband_id: ReceiveData() for subband_id in range(1, self.num_subbands + 1)}

    def deconfigure_scan(self: PstReceiveSimulator) -> None:
        """Simulate deconfiguring of a scan."""
        self._scan = False

    def start_scan(self: PstReceiveSimulator, args: dict) -> None:
        """Simulate start scanning.

        :param: the scan arguments.
        """
        self._scan = True

    def stop_scan(self: PstReceiveSimulator) -> None:
        """Simulate stop scanning."""
        self._scan = False

    def abort(self: PstReceiveSimulator) -> None:
        """Tell the component to abort whatever it was doing."""
        self._scan = False

    def reset(self: PstReceiveSimulator) -> None:
        """Tell the component to reset whatever it was doing."""
        self._scan = False

    def _update(self: PstReceiveSimulator) -> None:
        """Simulate the update of RECV data."""
        for subband_data in self._subband_data.values():
            update: ReceiveData = generate_random_update()

            subband_data.received_rate = update.received_rate
            subband_data.received_data += update.received_data
            subband_data.dropped_rate = update.dropped_rate
            subband_data.dropped_data += update.dropped_data
            subband_data.misordered_packets += update.misordered_packets

    def get_data(self: PstReceiveSimulator) -> ReceiveData:
        """
        Get current RECV data.

        Updates the current simulated data and returns the latest data.

        :returns: current simulated RECV data.
        :rtype: :py:class:`ReceiveData`
        """
        if self._scan:
            self._update()

        data = ReceiveData()
        for subband_data in self._subband_data.values():
            data.dropped_data += subband_data.dropped_data
            data.dropped_rate += subband_data.dropped_rate
            data.misordered_packets += subband_data.misordered_packets
            data.received_data += data.received_data
            data.received_rate += data.received_rate

        return data

    def get_subband_data(self: PstReceiveSimulator) -> Dict[int, ReceiveData]:
        """Get simulated subband data."""
        if self._scan:
            self._update()

        return self._subband_data
