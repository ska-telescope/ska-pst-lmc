# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the model data classes for DSP."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import List

from ska_pst_lmc.component import MonitorDataStore

# Need a default recording time that won't set off DSP device alarm
# use 1 year in seconds (as float)
DEFAULT_RECORDING_TIME: float = float(60 * 60 * 24 * 365)


@dataclass
class DspDiskSubbandMonitorData:
    """A data class to represent a subband monitoring data record.

    This class is used to report on a subband specific monitoring data.
    Each subband will report on the disk capacity and availabile bytes
    to help with the calculation of available recording time left for
    the whole beam.

    :ivar disk_capacity: total amount of bytes for the disk used for DSP
        processing for the beam.
    :vartype disk_capacity: int
    :ivar disk_available_bytes: total currently available bytes of the disk used.
    :vartype disk_available_bytes: int
    :ivar bytes_written: amount of bytes written by the subband in current scan.
    :vartype bytes_written: int
    :ivar write_rate: current rate of writing of data to disk for subband.
    :vartype write_rate: float
    """

    disk_capacity: int
    disk_available_bytes: int
    bytes_written: int
    write_rate: float


@dataclass
class DspDiskMonitorData:
    """A data class to represent the DSP monitoring across all subbands.

    This class is used to model the combined subband data for the DSP.
    Which includes the disk usage and monitoring as well as the
    current throughput of data.

    :ivar disk_capacity: size, in bytes, for the disk for DSP processing for
        this beam.
    :vartype disk_capacity: int
    :ivar disk_available_bytes: currently available bytes of the disk.
    :vartype disk_available_bytes: int
    :ivar bytes_written: total amount of bytes written in current scan across
        all subbands of the beam.
    :vartype bytes_written: int
    :ivar write_rate: total rate of writing to disk across all subbands, in
        bytes/second.
    :vartype write_rate: float
    :ivar available_recording_time: estimated available recording time left for
        current scan.
    :vartype available_recording_time: float
    :ivar subband_bytes_written: a list of bytes written, one record per subband.
    :vartype subband_bytes_written: List[int]
    :ivar subband_write_rate: a list of current rate of writing per subband,
        in bytes/seconds.
    :vartype subband_write_rate: List[float]
    """

    disk_capacity: int = field(default=sys.maxsize)
    disk_available_bytes: int = field(default=sys.maxsize)
    bytes_written: int = field(default=0)
    write_rate: float = field(default=0.0)
    available_recording_time: float = field(default=DEFAULT_RECORDING_TIME)
    subband_bytes_written: List[int] = field(default_factory=list)
    subband_write_rate: List[float] = field(default_factory=list)

    @property
    def disk_used_bytes(self: DspDiskMonitorData) -> int:
        """Get amount of bytes used on the disk that DSP is writing to."""
        return self.disk_capacity - self.disk_available_bytes

    @property
    def disk_used_percentage(self: DspDiskMonitorData) -> float:
        """Get the percentage of used disk space that DSP is writing to."""
        return 100.0 * (self.disk_used_bytes) / (self.disk_capacity + 1e-8)


class DspDiskMonitorDataStore(MonitorDataStore[DspDiskSubbandMonitorData, DspDiskMonitorData]):
    """Data store used to aggregate the subband data for DSP."""

    _disk_capacity: int
    _disk_available_bytes: int

    def __init__(self: DspDiskMonitorDataStore) -> None:
        """Initialise data monitor store."""
        # default disk available bytes to being Python's max sized int.
        self._disk_available_bytes = sys.maxsize
        self._disk_capacity = sys.maxsize
        super().__init__()

    def update_disk_stats(
        self: DspDiskMonitorDataStore, disk_capacity: int, disk_available_bytes: int
    ) -> None:
        """Update disk statistics.

        :param disk_capacity: the total disk capacity.
        :type disk_capacity: int
        :param disk_available_bytes: the available amount of disk space.
        :type disk_available_bytes: int
        """
        self._disk_capacity = disk_capacity
        self._disk_available_bytes = disk_available_bytes

    @property
    def monitor_data(self: DspDiskMonitorDataStore) -> DspDiskMonitorData:
        """Get current monitoring data for DSP.

        This returns the latest monitoring data calculated from the current
        subband data. If no subband data is available then the response is
        a default :py:class:`DspDiskMonitorData` object.
        """
        number_subbands: int = len(self._subband_data)
        if number_subbands == 0:
            # always used the last value stored, rather than
            # returning the default value.
            return DspDiskMonitorData(
                disk_available_bytes=self._disk_available_bytes, disk_capacity=self._disk_capacity
            )

        # use max long as initial value, we will want min value
        disk_capacity: int = sys.maxsize
        disk_available_bytes: int = sys.maxsize
        bytes_written: int = 0
        write_rate: float = 0.0

        subband_bytes_written: List[int] = number_subbands * [0]
        subband_write_rate: List[float] = number_subbands * [0.0]

        for subband_id, subband_data in self._subband_data.items():
            disk_capacity = min(disk_capacity, subband_data.disk_capacity)
            disk_available_bytes = min(disk_available_bytes, subband_data.disk_available_bytes)

            idx = subband_id - 1

            bytes_written += subband_data.bytes_written
            subband_bytes_written[idx] = subband_data.bytes_written

            write_rate += subband_data.write_rate
            subband_write_rate[idx] = subband_data.write_rate

        # need to reduce the recording time per disk A/(total current rate)
        available_recording_time = disk_available_bytes / (write_rate + 1e-8)

        self._disk_available_bytes = disk_available_bytes
        self._disk_capacity = disk_capacity

        return DspDiskMonitorData(
            disk_capacity=disk_capacity,
            disk_available_bytes=disk_available_bytes,
            bytes_written=bytes_written,
            write_rate=write_rate,
            available_recording_time=available_recording_time,
            subband_bytes_written=subband_bytes_written,
            subband_write_rate=subband_write_rate,
        )
