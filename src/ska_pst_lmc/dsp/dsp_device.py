# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing the DSP capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

import dataclasses
from typing import Any, List, Optional

import tango
from ska_tango_base.control_model import SimulationMode
from tango import DebugIt
from tango.server import attribute, command, device_property, run

import ska_pst_lmc.release as release
from ska_pst_lmc.component import as_device_attribute_name
from ska_pst_lmc.component.pst_device import PstBaseProcessDevice
from ska_pst_lmc.dsp.dsp_component_manager import PstDspComponentManager
from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorData

__all__ = ["PstDsp", "main"]


class PstDsp(PstBaseProcessDevice[PstDspComponentManager, DspDiskMonitorData]):
    """A software TANGO device for managing the DSP component of the PST.LMC subsystem."""

    # -----------------
    # Device Properties
    # -----------------
    process_api_endpoint = device_property(dtype=str, doc="Endpoint for the DSP.CORE service.")

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstDsp) -> None:
        """
        Initialise the attributes and properties of the PstDsp.

        This overrides the :py:class:`SKABaseDevice`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for f in dataclasses.fields(DspDiskMonitorData):
            self.set_change_event(as_device_attribute_name(f.name), True, False)
            self.set_archive_event(as_device_attribute_name(f.name), True, False)

        for n in ["diskUsedBytes", "diskUsedPercentage"]:
            self.set_change_event(n, True, False)
            self.set_archive_event(n, True, False)

    def create_component_manager(
        self: PstDsp,
    ) -> PstDspComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        self._monitoring_polling_rate = self.initial_monitoring_polling_rate

        return PstDspComponentManager(
            device_interface=self,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
        )

    def always_executed_hook(self: PstDsp) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstDsp) -> None:
        """
        Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the init_device method to be
        released.  This method is called by the device destructor and by the device Init command.
        """
        self.component_manager.stop_disk_stats_monitoring()
        super().delete_device()

    def handle_monitor_data_update(self: PstDsp, monitor_data: DspDiskMonitorData) -> None:
        """
        Handle monitoring data.

        :param monitor_data: the latest monitoring data that has been reported.
        :type monitor_data: DspDiskMonitorData
        """
        values = {
            **dataclasses.asdict(monitor_data),
            "disk_used_bytes": monitor_data.disk_used_bytes,
            "disk_used_percentage": monitor_data.disk_used_percentage,
        }

        for (key, value) in values.items():
            self.handle_attribute_value_update(key, value)

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total capacity of the disk that DSP is writing to.",
    )
    def diskCapacity(self: PstDsp) -> int:
        """
        Total capacity of the disk that DSP is writing to.

        :returns: total capacity of the disk that DSP is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.disk_capacity

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Available space on the disk that DSP is writing to.",
    )
    def availableDiskSpace(self: PstDsp) -> int:
        """
        Available space on the disk that DSP is writing to.

        :returns: available space on the disk that DSP is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.available_disk_space

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Used space on the disk that DSP is writing to.",
    )
    def diskUsedBytes(self: PstDsp) -> int:
        """
        Get sed space on the disk that DSP is writing to.

        This is `diskCapacity - availableDiskSpace`.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.disk_used_bytes

    @attribute(
        dtype=float,
        unit="Percentage",
        display_unit="%",
        max_value=100,
        min_value=0,
        max_alarm=99,
        max_warning=95,
        doc="Used space on the disk that DSP is writing to.",
    )
    def diskUsedPercentage(self: PstDsp) -> float:
        """
        Get used space on the disk that DSP is writing to.

        This is `100.0 * (diskCapacity - availableDiskSpace)/availableDiskSpace`.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.disk_used_percentage

    @attribute(
        dtype=float,
        unit="Bytes per second",
        display_unit="B/s",
        doc="Current rate of writing to the disk.",
    )
    def dataRecordRate(self: PstDsp) -> float:
        """
        Get current rate of writing to the disk.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.data_record_rate

    @attribute(
        dtype=int,
        unit="Bytes",
        display_unit="B",
        doc="Number of bytes written during scan.",
    )
    def dataRecorded(self: PstDsp) -> int:
        """
        Get number of bytes written during scan.

        :returns: number of bytes written during scan.
        :rtype: int
        """
        return self.component_manager.data_recorded

    @attribute(
        dtype=float,
        unit="Seconds",
        display_unit="s",
        min_alarm=10.0,
        min_warning=60.0,
        doc="Available time, in seconds, for writing available.",
    )
    def availableRecordingTime(self: PstDsp) -> float:
        """
        Get current rate of writing to the disk.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.available_recording_time

    @attribute(
        dtype=(int,),
        max_dim_x=4,
        unit="Bytes",
        display_unit="B",
        doc="The bytes per written for each subband",
    )
    def subbandDataRecorded(self: PstDsp) -> List[int]:
        """
        Get the bytes per written for each subband.

        :returns: the bytes per written for each subband.
        :rtype: List[int]
        """
        return self.component_manager.subband_data_recorded

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        unit="Bytes per second",
        display_unit="B/s",
        doc="The current rate of writing to disk for each subband",
    )
    def subbandDataRecordRate(self: PstDsp) -> List[float]:
        """
        Get the current rate of writing to disk for each subband.

        :returns: the current rate of writing to disk for each subband.
        :rtype: List[float]
        """
        return self.component_manager.subband_data_record_rate

    # --------
    # Commands
    # --------
    @command(
        dtype_out=("str",),
        doc_out="Version strings",
    )
    @DebugIt()
    def GetVersionInfo(self: PstDsp) -> List[str]:
        """
        Return the version information of the device.

        :return: The result code and the command unique ID
        """
        return [f"{self.__class__.__name__}, {self._build_state}"]


# ----------
# Run server
# ----------


def main(args: Optional[list] = None, **kwargs: Any) -> int:
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments
    :return: exit code
    :rtype: int
    """
    return run((PstDsp,), args=args, **kwargs)


if __name__ == "__main__":
    main()
