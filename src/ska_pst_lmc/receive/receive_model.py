# -*- coding: utf-8 -*-
#
# This file is part of the PstReceive project
#
#
#
# Distributed under the terms of the BSD3 license.
# See LICENSE.txt for more info.

"""Module for providing common model classes within the RECV sub-element component."""

from __future__ import annotations

from typing import List, NamedTuple


class ReceiveData(NamedTuple):
    """Named tuple used to transfer current RECV data between the process and the component manager.

    :ivar received_data: amount of data received during current scan, in bytes.
    :vartype received_data: int
    :ivar received_rate: the rate of data received during current scan, in Gb/s.
    :vartype received_rate: float
    :ivar dropped_data: amount of data dropped during current scan, in bytes.
    :vartype dropped_data: int
    :ivar dropped_rate: the rate of data dropped during current scan, in Gb/s.
    :vartype dropped_rate: float
    :ivar malformed_packets: the number of malformed packets received during current scan.
    :vartype malformed_packets: int
    :ivar misordered_packets: the number of misordered packets received during current scan.
    :vartype misordered_packets: int
    :ivar relative_weights: the relative weights for each channel.
    :vartype relative_weights: List[float]
    :ivar relative_weight: the average relative weight over all channels.
    :vartype relative_weight: float
    """

    received_data: int
    received_rate: float
    dropped_data: int
    dropped_rate: float
    malformed_packets: int
    misordered_packets: int
    relative_weights: List[float]
    relative_weight: float

    @staticmethod
    def defaults() -> ReceiveData:
        """Return a default ReceiveData object.

        This is used when the API is not connected or scanning.
        """
        return ReceiveData(
            received_data=0,
            received_rate=0.0,
            dropped_data=0,
            dropped_rate=0.0,
            misordered_packets=0,
            malformed_packets=0,
            relative_weights=[],
            relative_weight=0.0,
        )
