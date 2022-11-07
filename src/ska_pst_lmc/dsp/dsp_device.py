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
from ska_pst_lmc.component.pst_device import PstBaseProccesDevice
from ska_pst_lmc.dsp.dsp_component_manager import PstDspComponentManager
from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorData

__all__ = ["PstDsp", "main"]


class PstDsp(PstBaseProccesDevice[PstDspComponentManager]):
    """A software TANGO device for managing the DSP component of the PST.LMC subsystem."""

    # -----------------
    # Device Properties
    # -----------------
    process_api_endpoint = device_property(dtype=str, doc="Endpoint for the DSP.CORE service.")

    monitor_polling_rate = device_property(
        dtype=int, default_value=5000, doc="Rate at which monitor polling should happen, in milliseconds."
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstDsp) -> None:
        """Initialise the attributes and properties of the PstDsp.

        This overrides the :py:class:`SKABaseDevice`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for f in dataclasses.fields(DspDiskMonitorData):
            self.set_change_event(f.name, True, True)
            self.set_archive_event(f.name, True)

        for n in ["disk_used_bytes", "disk_used_percentage"]:
            self.set_change_event(n, True, True)
            self.set_archive_event(n, True)

    def create_component_manager(
        self: PstDsp,
    ) -> PstDspComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstDspComponentManager(
            device_name=self.get_name(),
            process_api_endpoint=self.process_api_endpoint,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            monitor_polling_rate=self.monitor_polling_rate,
            monitor_data_callback=self._update_monitor_data,
            beam_id=self.DeviceID,
        )

    def always_executed_hook(self: PstDsp) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstDsp) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    def _update_monitor_data(self: PstDsp, data: DspDiskMonitorData) -> None:
        values = {
            **dataclasses.asdict(data),
            "disk_used_bytes": data.disk_used_bytes,
            "disk_used_percentage": data.disk_used_percentage,
        }

        for (key, value) in values.items():
            self.push_change_event(key, value)
            self.push_archive_event(key, value)

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevULong64",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total capacity of the disk that DSP is writing to.",
    )
    def disk_capacity(self: PstDsp) -> int:
        """Total capacity of the disk that DSP is writing to.

        :returns: total capacity of the disk that DSP is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.disk_capacity

    @attribute(
        dtype="DevULong64",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Available space on the disk that DSP is writing to.",
    )
    def disk_available_bytes(self: PstDsp) -> int:
        """Available space on the disk that DSP is writing to.

        :returns: available space on the disk that DSP is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.disk_available_bytes

    @attribute(
        dtype="DevULong64",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Used space on the disk that DSP is writing to.",
    )
    def disk_used_bytes(self: PstDsp) -> int:
        """Get sed space on the disk that DSP is writing to.

        This is `disk_capacity` - `disk_available_bytes`.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.disk_used_bytes

    @attribute(
        dtype="DevFloat",
        unit="Percentage",
        display_unit="%",
        max_value=100,
        min_value=0,
        max_alarm=90,
        max_warning=80,
        doc="Used space on the disk that DSP is writing to.",
    )
    def disk_used_percentage(self: PstDsp) -> float:
        """Get used space on the disk that DSP is writing to.

        This is `disk_capacity` - `disk_available_bytes`.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.disk_used_percentage

    @attribute(
        dtype="DevFloat",
        unit="Bytes per second",
        display_unit="B/s",
        doc="Current rate of writing to the disk.",
    )
    def write_rate(self: PstDsp) -> float:
        """Get current rate of writing to the disk.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.write_rate

    @attribute(
        dtype="DevULong64",
        unit="Bytes",
        display_unit="B",
        doc="Number of bytes written during scan.",
    )
    def bytes_written(self: PstDsp) -> int:
        """Get number of bytes written during scan.

        :returns: number of bytes written during scan.
        :rtype: int
        """
        return self.component_manager.bytes_written

    @attribute(
        dtype="DevFloat",
        unit="Seconds",
        display_unit="s",
        min_alarm=10.0,
        min_warning=60.0,
        doc="Available time, in seconds, for writing available.",
    )
    def available_recording_time(self: PstDsp) -> float:
        """Get current rate of writing to the disk.

        :returns: use space on the disk that DSP is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.available_recording_time

    @attribute(
        dtype=("DevULong64",),
        max_dim_x=4,
        unit="Bytes",
        display_unit="B",
        doc="The bytes per written for each subband",
    )
    def subband_bytes_written(self: PstDsp) -> List[int]:
        """Get the bytes per written for each subband.

        :returns: the bytes per written for each subband.
        :rtype: List[int]
        """
        return self.component_manager.subband_bytes_written

    @attribute(
        dtype=("DevFloat",),
        max_dim_x=4,
        unit="Bytes per second",
        display_unit="B/s",
        doc="The current rate of writing to disk for each subband",
    )
    def subband_write_rate(self: PstDsp) -> List[float]:
        """Get the current rate of writing to disk for each subband.

        :returns: the current rate of writing to disk for each subband.
        :rtype: List[float]
        """
        return self.component_manager.subband_write_rate

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
