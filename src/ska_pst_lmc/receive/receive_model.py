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
    :ivar dropped_data: amount of data dropped during current scan, in bytes.
    :vartype dropped_data: int
    :ivar dropped_rate: the rate of data dropped during current scan, in Bytes/s.
    :vartype dropped_rate: float
    :ivar misordered_packets: the number of misordered packets received during current scan.
    :vartype misordered_packets: int
    """

    data_received: int = 0
    data_receive_rate: float = 0.0
    dropped_data: int = 0
    dropped_rate: float = 0.0
    misordered_packets: int = 0


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
            monitor_data.dropped_data += subband_monitor_data.dropped_data
            monitor_data.dropped_rate += subband_monitor_data.dropped_rate
            monitor_data.data_received += subband_monitor_data.data_received
            monitor_data.data_receive_rate += subband_monitor_data.data_receive_rate
            monitor_data.misordered_packets += subband_monitor_data.misordered_packets

        return monitor_data
