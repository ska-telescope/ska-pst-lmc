# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing common model classes within the RECV sub-element component."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReceiveData:
    """A data class to transfer current RECV data between the process and the component manager.

    :ivar received_data: amount of data received during current scan, in bytes.
    :vartype received_data: int
    :ivar received_rate: the rate of data received during current scan, in Gb/s.
    :vartype received_rate: float
    :ivar dropped_data: amount of data dropped during current scan, in bytes.
    :vartype dropped_data: int
    :ivar dropped_rate: the rate of data dropped during current scan, in Gb/s.
    :vartype dropped_rate: float
    :ivar misordered_packets: the number of misordered packets received during current scan.
    :vartype misordered_packets: int
    """

    received_data: int = 0
    received_rate: float = 0.0
    dropped_data: int = 0
    dropped_rate: float = 0.0
    misordered_packets: int = 0
