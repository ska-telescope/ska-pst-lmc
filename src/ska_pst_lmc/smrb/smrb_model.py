# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing common model classes within the SMRB.MGMT component."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ska_pst_lmc.component import MonitorDataStore


@dataclass
class SmrbMonitorData:
    """
    A data class for transfer current SMRB data between the process and the component manager.

    :ivar ring_buffer_utilisation: current utilisation of the overall ring buffer.
    :vartype ring_buffer_utilisation: float
    :ivar ring_buffer_size: the size of the ring buffer, in bytes.
    :vartype ring_buffer_size: int
    :ivar ring_buffer_read: the amount of data, in bytes, read from ring buffer.
    :vartype ring_buffer_read: int
    :ivar ring_buffer_written: the amount of data, in bytes, written to ring buffer.
    :vartype ring_buffer_written: int
    :ivar number_subbands: the number of subbands the ring buffer is configured for.
    :vartype number_subbands: int
    :ivar subband_ring_buffer_utilisations: a list of utilisation for each subband.
    :vartype subband_ring_buffer_utilisations: List[float]
    :ivar subband_ring_buffer_sizes: the allocated size of each subband within the ring buffer, in bytes.
    :vartype subband_ring_buffer_sizes: List[int]
    :ivar subband_ring_buffer_read: the amount of data, in bytes, read from each sub-band.
    :vartype subband_ring_buffer_read: int
    :ivar subband_ring_buffer_written: the amount of data, in bytes, written to each sub-band.
    :vartype subband_ring_buffer_written: List[int]
    """

    ring_buffer_utilisation: float = 0.0
    ring_buffer_size: int = 0
    ring_buffer_read: int = 0
    ring_buffer_written: int = 0
    number_subbands: int = 0
    subband_ring_buffer_utilisations: List[float] = field(default_factory=list)
    subband_ring_buffer_sizes: List[int] = field(default_factory=list)
    subband_ring_buffer_read: List[int] = field(default_factory=list)
    subband_ring_buffer_written: List[int] = field(default_factory=list)


@dataclass
class SmrbSubbandMonitorData:
    """
    A data class used for a specific SMRB subband.

    :ivar buffer_size: total size of the ring buffer, including header size.
    :vartype buffer_size: int
    :ivar total_written: total amount of data, in bytes, written to the ring buffer during scan.
    :vartype total_written: int
    :ivar total_read: total amount of data, in bytes, read from the ring buffer during scan.
    :vartype total_read: int
    :ivar full: the number of buffers currently in use. Needed for aggregation for the whole SMRB stats.
    :vartype full: int
    :ivar full: the number of buffers for subband. Needed for aggregation for the whole SMRB stats.
    :vartype full: int
    """

    buffer_size: int
    num_of_buffers: int
    total_written: int = 0
    total_read: int = 0
    full: int = 0

    @property
    def utilisation(self: SmrbSubbandMonitorData) -> float:
        """
        Return the current utilisation of the subband ring buffer.

        This is full/num_of_buffers as a percentage.
        """
        return self.full / self.num_of_buffers * 100.0

    @property
    def utilised_bytes(self: SmrbSubbandMonitorData) -> float:
        """
        Return the number of utilised bytes.

        This is utiltisation (as float not percentage) * buffer_size. Which is equivalent to
        full/num_of_buffers * buffer_size.
        """
        return self.full / self.num_of_buffers * self.buffer_size


class SmrbMonitorDataStore(MonitorDataStore[SmrbSubbandMonitorData, SmrbMonitorData]):
    """Data store use to aggregate the subband data."""

    @property
    def monitor_data(self: SmrbMonitorDataStore) -> SmrbMonitorData:
        """
        Calculate the aggregate SMRB monitor data.

        This step includes rolling up each of the individual sub-band data
        items to be able to calculate the overall utilisation

        :returns: the calculated monitoring data. If there is no subband data
            this will return a default instance of a :py:class:`SmrbMonitorData`.
        """
        number_subbands: int = len(self._subband_data)
        if number_subbands == 0:
            # no ringbuffer has been allocated, so return empty data
            return SmrbMonitorData()

        ring_buffer_utilisation: float = 0.0
        ring_buffer_size: int = 0
        ring_buffer_read: int = 0
        ring_buffer_written: int = 0

        # initialise subband data to zeros
        subband_ring_buffer_utilisations: List[float] = number_subbands * [0.0]
        subband_ring_buffer_sizes: List[int] = number_subbands * [0]
        subband_ring_buffer_read: List[int] = number_subbands * [0]
        subband_ring_buffer_written: List[int] = number_subbands * [0]

        total_utilised_bytes: float = 0.0

        for subband_id, data in self._subband_data.items():
            # need a zero offset
            idx = subband_id - 1
            ring_buffer_size += data.buffer_size
            ring_buffer_read += data.total_read
            ring_buffer_written += data.total_written
            total_utilised_bytes += data.utilised_bytes

            subband_ring_buffer_utilisations[idx] = data.utilisation
            subband_ring_buffer_sizes[idx] = data.buffer_size
            subband_ring_buffer_read[idx] = data.total_read
            subband_ring_buffer_written[idx] = data.total_written

        if ring_buffer_size > 0:
            # avoid true divide by zero.  This should not happen
            # if the ring buffers have been allocated.
            ring_buffer_utilisation = total_utilised_bytes / ring_buffer_size * 100.0

        return SmrbMonitorData(
            ring_buffer_utilisation=ring_buffer_utilisation,
            ring_buffer_size=ring_buffer_size,
            ring_buffer_read=ring_buffer_read,
            ring_buffer_written=ring_buffer_written,
            number_subbands=number_subbands,
            subband_ring_buffer_utilisations=subband_ring_buffer_utilisations,
            subband_ring_buffer_sizes=subband_ring_buffer_sizes,
            subband_ring_buffer_read=subband_ring_buffer_read,
            subband_ring_buffer_written=subband_ring_buffer_written,
        )
