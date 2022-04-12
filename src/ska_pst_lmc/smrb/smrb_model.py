# -*- coding: utf-8 -*-
#
# This file is part of the PstReceive project
#
#
#
# Distributed under the terms of the BSD3 license.
# See LICENSE.txt for more info.

"""Module for providing common model classes within the SMRB sub-element component."""

from __future__ import annotations

from typing import List, NamedTuple


class SharedMemoryRingBufferData(NamedTuple):
    """Named tuple used to transfer current SMRB data between the process and the component manager.

    :ivar ring_buffer_utilisation: current utilisation of the overall ring buffer.
    :vartype ring_buffer_utilisation: float
    :ivar ring_buffer_size: the size of the ring buffer, in bytes.
    :vartype ring_buffer_size: int
    :ivar number_subbands: the number of subbands the ring buffer is configured for.
    :vartype number_subbands: int
    :ivar subband_ring_buffer_utilisations: a list of utilisation for each subband.
    :vartype subband_ring_buffer_utilisations: list[float]
    :ivar subband_ring_buffer_sizes: the allocated size of each subband within the ring buffer, in bytes.
    :vartype subband_ring_buffer_sizes: list[int]
    """

    ring_buffer_utilisation: float
    ring_buffer_size: int
    number_subbands: int
    subband_ring_buffer_utilisations: List[float]
    subband_ring_buffer_sizes: List[int]

    @staticmethod
    def defaults() -> SharedMemoryRingBufferData:
        """Return a default SharedMemoryRingBufferData object.

        This is used when the API is not connected or scanning.
        """
        return SharedMemoryRingBufferData(
            ring_buffer_utilisation=0.0,
            ring_buffer_size=1024,
            number_subbands=4,
            subband_ring_buffer_utilisations=4 * [0.0],
            subband_ring_buffer_sizes=4 * [256],
        )
