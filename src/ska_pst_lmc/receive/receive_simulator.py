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
    data_receive_rate: float = 1.0 * randint(0, 90)
    data_received: int = int(data_receive_rate * 1e9 / 8)

    data_drop_rate: float = data_receive_rate / 1000.0 * random()
    data_dropped: int = int(data_drop_rate * 1e9 / 8)

    misordered_packets: int = randint(0, 3)
    misordered_packet_rate: float = 1.0 * misordered_packets

    malformed_packets: int = randint(0, 3)
    malformed_packet_rate: float = 1.0 * malformed_packets

    misdirected_packets: int = randint(0, 3)
    misdirected_packet_rate: float = 1.0 * misordered_packets

    checksum_failure_packets: int = randint(0, 3)
    checksum_failure_packet_rate: float = 1.0 * checksum_failure_packets

    timestamp_sync_error_packets: int = randint(0, 3)
    timestamp_sync_error_packet_rate: float = 1.0 * timestamp_sync_error_packets

    seq_number_sync_error_packets: int = randint(0, 3)
    seq_number_sync_error_packet_rate: float = 1.0 * seq_number_sync_error_packets

    return ReceiveData(
        data_received=data_received,
        data_receive_rate=data_receive_rate,
        data_dropped=data_dropped,
        data_drop_rate=data_drop_rate,
        misordered_packets=misordered_packets,
        misordered_packet_rate=misordered_packet_rate,
        malformed_packets=malformed_packets,
        malformed_packet_rate=malformed_packet_rate,
        misdirected_packets=misdirected_packets,
        misdirected_packet_rate=misdirected_packet_rate,
        checksum_failure_packets=checksum_failure_packets,
        checksum_failure_packet_rate=checksum_failure_packet_rate,
        timestamp_sync_error_packets=timestamp_sync_error_packets,
        timestamp_sync_error_packet_rate=timestamp_sync_error_packet_rate,
        seq_number_sync_error_packets=seq_number_sync_error_packets,
        seq_number_sync_error_packet_rate=seq_number_sync_error_packet_rate,
    )


class PstReceiveSimulator:
    """
    Simulator for the RECV process of the PST.LMC sub-system.

    This is used to generate random data and simulate what happens during the RECV process. Current
    implementation has this internally with the TANGO device but future improvements will have this as a
    separate process and the TANGO will connect via an API.
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
        """
        Simulate start scanning.

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

            # update totals
            subband_data.data_received += update.data_received
            subband_data.data_dropped += update.data_dropped
            subband_data.misordered_packets += update.misordered_packets
            subband_data.malformed_packets += update.malformed_packets
            subband_data.misdirected_packets += update.misdirected_packets
            subband_data.checksum_failure_packets += update.checksum_failure_packets
            subband_data.timestamp_sync_error_packets += update.timestamp_sync_error_packets
            subband_data.seq_number_sync_error_packets += update.seq_number_sync_error_packets

            # update the rates
            subband_data.data_receive_rate = update.data_receive_rate
            subband_data.data_drop_rate = update.data_drop_rate
            subband_data.misordered_packet_rate = update.misordered_packet_rate
            subband_data.malformed_packet_rate = update.malformed_packet_rate
            subband_data.misdirected_packet_rate = update.misdirected_packet_rate
            subband_data.checksum_failure_packet_rate = update.checksum_failure_packet_rate
            subband_data.timestamp_sync_error_packet_rate = update.timestamp_sync_error_packet_rate
            subband_data.seq_number_sync_error_packet_rate = update.seq_number_sync_error_packet_rate

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
            data.data_dropped += subband_data.data_dropped
            data.data_drop_rate += subband_data.data_drop_rate
            data.data_received += subband_data.data_received
            data.data_receive_rate += subband_data.data_receive_rate
            data.misordered_packets += subband_data.misordered_packets
            data.misordered_packet_rate += subband_data.misordered_packet_rate
            data.malformed_packets += subband_data.malformed_packets
            data.malformed_packet_rate += subband_data.malformed_packet_rate
            data.misdirected_packets += subband_data.misdirected_packets
            data.misdirected_packet_rate += subband_data.misdirected_packet_rate
            data.checksum_failure_packets += subband_data.checksum_failure_packets
            data.checksum_failure_packet_rate += subband_data.checksum_failure_packet_rate
            data.timestamp_sync_error_packets += subband_data.timestamp_sync_error_packets
            data.timestamp_sync_error_packet_rate += subband_data.timestamp_sync_error_packet_rate
            data.seq_number_sync_error_packets += subband_data.seq_number_sync_error_packets
            data.seq_number_sync_error_packet_rate += subband_data.seq_number_sync_error_packet_rate

        return data

    def get_subband_data(self: PstReceiveSimulator) -> Dict[int, ReceiveData]:
        """Get simulated subband data."""
        if self._scan:
            self._update()

        return self._subband_data
