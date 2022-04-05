# -*- coding: utf-8 -*-
#
# This file is part of the PstReceive project
#
#
#
# Distributed under the terms of the BSD3 license.
# See LICENSE.txt for more info.

"""Module for providing common model classes within the RECV sub-element component."""

from collections import namedtuple


class ReceiveData(
    namedtuple(
        "ReceiveData",
        [
            "received_data",
            "received_rate",
            "dropped_data",
            "dropped_rate",
            "misordeded_packets",
            "malformed_packets",
            "relative_weights",
            "relative_weight",
        ],
    )
):
    """Named tuple used to transfer current RECV data between the process and the component manager.

    :ivar received_data: amount of data received during current scan, in bytes.
    :ivar received_rate: the rate of data received during current scan, in Gb/s.
    :ivar dropped_data: amount of data dropped during current scan, in bytes.
    :ivar dropped_rate: the rate of data dropped during current scan, in Gb/s.
    :ivar malformed_packets: the number of malformed packets received during current scan.
    :ivar relative_weights: the relative weights for each channel.
    :ivar relative_weight: the average relative weight over all channels.
    """

    __slots__ = ()
