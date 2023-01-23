# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing common model classes within the RECV.MGMT component."""

from __future__ import annotations

from dataclasses import dataclass

from ska_pst_lmc.component.monitor_data_handler import MonitorDataStore


@dataclass
class ReceiveData:
    """A data class to transfer current RECV data between the process and the component manager.

    :ivar data_received: amount of data received during current scan, in bytes.
    :vartype data_received: int
    :ivar data_receive_rate: the rate of data received during current scan, in Gb/s.
    :vartype data_receive_rate: float
    :ivar data_dropped: amount of data dropped during current scan, in bytes.
    :vartype data_dropped: int
    :ivar data_drop_rate: the rate of data dropped during current scan, in Bytes/s.
    :vartype data_drop_rate: float
    :ivar misordered_packets: the number of misordered packets received during current scan.
    :vartype misordered_packets: float
    :ivar malformed_packets: the total number of malformed packets during current scan.
    :vartype malformed_packets: int
    :ivar malformed_packet_rate: the current rate of malformed packets.
    :vartype malformed_packet_rate: float
    :ivar misdirected_packets: the total of misdirected packets for current scan. These
        are valid packets but not for the current beam, subband, and/or scan.
    :vartype misdirected_packets: int
    :ivar misdirected_packet_rate: the current rate of misdirected packets.
    :vartype misordered_packets: float
    :ivar checksum_failure_packets: the total number of network interface with
        either a UDP, IP header or CRC checksum failure.
    :vartype checksum_failure_packets: int
    :ivar checksum_failure_packet_rate: the current rate of packets with a checksum failure.
    :vartype checksum_failure_packet_rate: float
    :ivar timestamp_sync_error_packets: the total number of packets received
        where the timestamp has become desynchronised with the packet sequence
        number * sampling interval.
    :vartype timestamp_sync_error_packets: int
    :ivar timestamp_sync_error_packet_rate: the current rate of packets with
        timestamp sync error.
    :vartype timestamp_sync_error_packet_rate: float
    :ivar seq_number_sync_error_packets: the total number of packets received
        where the packet sequence number has become desynchronised with the
        data rate and elapsed time.
    :vartype seq_number_sync_error_packets: int
    :ivar seq_number_sync_error_packet_rate: the current rate of packets with
        a sequence number sync error.
    :vartype seq_number_sync_error_packet_rate: float
    """

    data_received: int = 0
    data_receive_rate: float = 0.0
    data_dropped: int = 0
    data_drop_rate: float = 0.0
    misordered_packets: int = 0
    misordered_packet_rate: float = 0.0
    malformed_packets: int = 0
    malformed_packet_rate: float = 0.0
    misdirected_packets: int = 0
    misdirected_packet_rate: float = 0.0
    checksum_failure_packets: int = 0
    checksum_failure_packet_rate: float = 0.0
    timestamp_sync_error_packets: int = 0
    timestamp_sync_error_packet_rate: float = 0.0
    seq_number_sync_error_packets: int = 0
    seq_number_sync_error_packet_rate: float = 0.0


class ReceiveDataStore(MonitorDataStore[ReceiveData, ReceiveData]):
    """A data store for Receive subband monitoring data.

    This data store will aggregate the separate data
    """

    @property
    def monitor_data(self: ReceiveDataStore) -> ReceiveData:
        """Return the current calculated monitoring data.

        This aggregates all the individual subband data values into one
        :py:class:`ReceiveData` instance.

        :returns: current monitoring data.
        """
        monitor_data = ReceiveData()
        for subband_monitor_data in self._subband_data.values():
            monitor_data.data_dropped += subband_monitor_data.data_dropped
            monitor_data.data_drop_rate += subband_monitor_data.data_drop_rate
            monitor_data.data_received += subband_monitor_data.data_received
            monitor_data.data_receive_rate += subband_monitor_data.data_receive_rate
            monitor_data.misordered_packets += subband_monitor_data.misordered_packets

        return monitor_data
