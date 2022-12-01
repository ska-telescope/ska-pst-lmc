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
    :ivar available_disk_space: total currently available bytes of the disk used.
    :vartype available_disk_space: int
    :ivar data_recorded: amount of bytes written by the subband in current scan.
    :vartype data_recorded: int
    :ivar data_record_rate: current rate of writing of data to disk for subband.
    :vartype data_record_rate: float
    """

    disk_capacity: int
    available_disk_space: int
    data_recorded: int
    data_record_rate: float


@dataclass
class DspDiskMonitorData:
    """A data class to represent the DSP monitoring across all subbands.

    This class is used to model the combined subband data for the DSP.
    Which includes the disk usage and monitoring as well as the
    current throughput of data.

    :ivar disk_capacity: size, in bytes, for the disk for DSP processing for
        this beam.
    :vartype disk_capacity: int
    :ivar available_disk_space: currently available bytes of the disk.
    :vartype available_disk_space: int
    :ivar data_recorded: total amount of bytes written in current scan across
        all subbands of the beam.
    :vartype data_recorded: int
    :ivar data_record_rate: total rate of writing to disk across all subbands, in
        bytes/second.
    :vartype data_record_rate: float
    :ivar available_recording_time: estimated available recording time left for
        current scan.
    :vartype available_recording_time: float
    :ivar subband_data_recorded: a list of bytes written, one record per subband.
    :vartype subband_data_recorded: List[int]
    :ivar subband_data_record_rate: a list of current rate of writing per subband,
        in bytes/seconds.
    :vartype subband_data_record_rate: List[float]
    """

    disk_capacity: int = field(default=sys.maxsize)
    available_disk_space: int = field(default=sys.maxsize)
    data_recorded: int = field(default=0)
    data_record_rate: float = field(default=0.0)
    available_recording_time: float = field(default=DEFAULT_RECORDING_TIME)
    subband_data_recorded: List[int] = field(default_factory=list)
    subband_data_record_rate: List[float] = field(default_factory=list)

    @property
    def disk_used_bytes(self: DspDiskMonitorData) -> int:
        """Get amount of bytes used on the disk that DSP is writing to."""
        return self.disk_capacity - self.available_disk_space

    @property
    def disk_used_percentage(self: DspDiskMonitorData) -> float:
        """Get the percentage of used disk space that DSP is writing to."""
        return 100.0 * (self.disk_used_bytes) / (self.disk_capacity + 1e-8)


class DspDiskMonitorDataStore(MonitorDataStore[DspDiskSubbandMonitorData, DspDiskMonitorData]):
    """Data store used to aggregate the subband data for DSP."""

    _disk_capacity: int
    _available_disk_space: int

    def __init__(self: DspDiskMonitorDataStore) -> None:
        """Initialise data monitor store."""
        # default disk available bytes to being Python's max sized int.
        self._available_disk_space = sys.maxsize
        self._disk_capacity = sys.maxsize
        super().__init__()

    def update_disk_stats(
        self: DspDiskMonitorDataStore, disk_capacity: int, available_disk_space: int
    ) -> None:
        """Update disk statistics.

        :param disk_capacity: the total disk capacity.
        :type disk_capacity: int
        :param available_disk_space: the available amount of disk space.
        :type available_disk_space: int
        """
        self._disk_capacity = disk_capacity
        self._available_disk_space = available_disk_space

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
                available_disk_space=self._available_disk_space, disk_capacity=self._disk_capacity
            )

        # use max long as initial value, we will want min value
        disk_capacity: int = sys.maxsize
        available_disk_space: int = sys.maxsize
        data_recorded: int = 0
        data_record_rate: float = 0.0

        subband_data_recorded: List[int] = number_subbands * [0]
        subband_data_record_rate: List[float] = number_subbands * [0.0]

        for subband_id, subband_data in self._subband_data.items():
            disk_capacity = min(disk_capacity, subband_data.disk_capacity)
            available_disk_space = min(available_disk_space, subband_data.available_disk_space)

            idx = subband_id - 1

            data_recorded += subband_data.data_recorded
            subband_data_recorded[idx] = subband_data.data_recorded

            data_record_rate += subband_data.data_record_rate
            subband_data_record_rate[idx] = subband_data.data_record_rate

        # need to reduce the recording time per disk A/(total current rate)
        available_recording_time = available_disk_space / (data_record_rate + 1e-8)

        self._available_disk_space = available_disk_space
        self._disk_capacity = disk_capacity

        return DspDiskMonitorData(
            disk_capacity=disk_capacity,
            available_disk_space=available_disk_space,
            data_recorded=data_recorded,
            data_record_rate=data_record_rate,
            available_recording_time=available_recording_time,
            subband_data_recorded=subband_data_recorded,
            subband_data_record_rate=subband_data_record_rate,
        )
