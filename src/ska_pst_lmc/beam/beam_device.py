# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Beam capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import Any, List, Optional

import tango
from ska_tango_base.control_model import AdminMode, SimulationMode
from tango import DebugIt
from tango.server import attribute, command, device_property, run

import ska_pst_lmc.release as release
from ska_pst_lmc.beam.beam_component_manager import PstBeamComponentManager
from ska_pst_lmc.component import as_device_attribute_name
from ska_pst_lmc.component.pst_device import PstBaseDevice
from ska_pst_lmc.dsp.dsp_model import DEFAULT_RECORDING_TIME

__all__ = ["PstBeam", "main"]


class PstBeam(PstBaseDevice[PstBeamComponentManager]):
    """A logical TANGO device representing a Beam Capability for PST.LMC.

    **Properties:**

    - Device Property
        RecvFQDN
            - Type:'DevString'
        SmrbFQDN
            - Type:'DevString'
        DspFQDN
            - Type:'DevString'
        SendFQDN
            - Type:'DevString'
    """

    # -----------------
    # Device Properties
    # -----------------

    RecvFQDN = device_property(
        dtype=str,
    )

    SmrbFQDN = device_property(
        dtype=str,
    )

    DspFQDN = device_property(
        dtype=str,
    )

    SendFQDN = device_property(
        dtype=str,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstBeam) -> None:
        """Initialise the attributes and properties of the PstReceive.

        This overrides the :py:class:`SKABaseDevice`.
        """
        import sys

        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        self._received_rate = 0.0
        self._received_data = 0
        self._dropped_rate = 0.0
        self._dropped_data = 0
        self._write_rate = 0.0
        self._bytes_written = 0
        self._ingest_configuration = ""
        self._disk_available_bytes = sys.maxsize
        self._available_recording_time = DEFAULT_RECORDING_TIME
        self._ring_buffer_utilisation = 0.0
        self._expected_data_rate = 0.0

        for prop in [
            "receivedRate",
            "receivedData",
            "droppedRate",
            "droppedData",
            "writeRate",
            "bytesWritten",
            "diskAvailableBytes",
            "expectedDataRate",
            "availableRecordingTime",
            "ringBufferUtilisation",
            "expectedDataRate",
        ]:
            self.set_change_event(prop, True, False)
            self.set_archive_event(prop, True, False)

    def create_component_manager(
        self: PstBeam,
    ) -> PstBeamComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstBeamComponentManager(
            device_name=self.get_name(),
            smrb_fqdn=self.SmrbFQDN,
            recv_fqdn=self.RecvFQDN,
            dsp_fqdn=self.DspFQDN,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            beam_id=self.DeviceID,
            property_callback=self._update_attribute_value,
        )

    def always_executed_hook(self: PstBeam) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstBeam) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    def _update_attribute_value(self: PstBeam, key: str, value: Any) -> None:
        try:
            setattr(self, f"_{key}", value)
            attr_key = as_device_attribute_name(key)
            self.push_change_event(attr_key, value)
            self.push_archive_event(attr_key, value)
        except Exception:
            self.logger.warning(f"Error in attempting to set device attribute {key}.", exc_info=True)

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=str,
        doc="The PST Ingest configuration as a JSON string",
    )
    def ingestConfiguration(self: PstBeam) -> str:
        """Get the PST Ingest configuration as a JSON string.

        This will return the JSON representation of the configuration
        that this PST Beam has configured for ingesting data. This
        configuration includes the following properties:

            * Number of channel blocks, between 1 and 4
            * For each channel block, the block of channel numbers
              using a range in the form of inclusive of the lower
              number and exclusive of the higher number (e.g [1, 21)
              would be a range of 20 channels starting from 1 and ending
              at channel block 20 (inclusive).
            * Channel block IPv4 address to send data to.
            * Channel block UDP port

        :returns: the PST Ingest configuration as a JSON string.
        :rtype: str
        """
        return self._ingest_configuration

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Available space on the disk that DSP is writing to.",
    )
    def diskAvailableBytes(self: PstBeam) -> int:
        """Available space on the disk that the PST.BEAM is writing to.

        :returns: available space on the disk that PST.BEAM is writing to, in bytes.
        :rtype: int
        """
        return self._disk_available_bytes

    @attribute(
        dtype=float,
        unit="Seconds",
        display_unit="s",
        min_alarm=10.0,
        min_warning=60.0,
        doc="Available time, in seconds, for writing available.",
    )
    def availableRecordingTime(self: PstBeam) -> float:
        """Get available time, in seconds, for writing available.

        :returns: available time, in seconds, for writing available.
        :rtype: float
        """
        return self._available_recording_time

    # Scan monitoring values
    @attribute(
        dtype=float,
        unit="Gigabits per second",
        standard_unit="Gigabits per second",
        display_unit="Gb/s",
        max_value=200,
        min_value=0,
        doc="Current data receive rate from the CBF interface",
    )
    def receivedRate(self: PstBeam) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self._received_rate

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total number of bytes received from the CBF in the current scan",
    )
    def receivedData(self: PstBeam) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self._received_data

    @attribute(
        dtype=float,
        label="Drop Rate",
        unit="Bytes per second",
        standard_unit="Bytes per second",
        display_unit="B/s",
        max_value=200,
        min_value=-1,
        max_alarm=10,
        min_alarm=-1,
        max_warning=1,
        min_warning=-1,
        doc="Current rate of CBF ingest data being dropped or lost by the receiving process",
    )
    def droppedRate(self: PstBeam) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in Bytes/s.
        :rtype: float
        """
        return self._dropped_rate

    @attribute(
        dtype=int,
        label="Dropped",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total number of bytes dropped in the current scan",
    )
    def droppedData(self: PstBeam) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan.
        :rtype: int
        """
        return self._dropped_data

    @attribute(
        dtype=float,
        unit="Bytes per second",
        display_unit="B/s",
        doc="Current rate of writing to the disk.",
    )
    def writeRate(self: PstBeam) -> float:
        """Get current rate of writing to the disk.

        :returns: use space on the disk that PST.BEAM is writing to, in bytes.
        :rtype: float
        """
        return self._write_rate

    @attribute(
        dtype=int,
        unit="Bytes",
        display_unit="B",
        doc="Number of bytes written during scan.",
    )
    def bytesWritten(self: PstBeam) -> int:
        """Get number of bytes written during scan.

        :returns: number of bytes written during scan.
        :rtype: int
        """
        return self._bytes_written

    @attribute(
        dtype=str,
        doc="The channel block configuration based on scan configuration.",
    )
    def channelBlockConfiguration(self: PstBeam) -> str:
        """Get the channel block configuration.

        This is a JSON serialised string of the channel block configuration
        that is calculated during the `ConfigureScan` command.

        :returns: the channel block configuration as a JSON string.
        :rtype: str
        """
        import json

        return json.dumps(self.component_manager.channel_block_configuration)

    @attribute(
        dtype=float,
        label="Utilisation",
        unit="Percentage",
        display_unit="%",
        max_value=100,
        min_value=0,
        max_alarm=90,
        max_warning=80,
        doc="Percentage of the ring buffer elements that are full of data",
    )
    def ringBufferUtilisation(self: PstBeam) -> float:
        """Get the percentage of the ring buffer elements that are full of data.

        :returns: the percentage of the ring buffer elements that are full of data.
        :rtype: float
        """
        return self._ring_buffer_utilisation

    @attribute(
        dtype=float,
        unit="Gigibits per second",
        display_unit="Gb/s",
        doc="Expected rate of data to be received by PST Beam component.",
    )
    def expectedDataRate(self: PstBeam) -> float:
        """Get the expected rate of data to be received by PST Beam component.

        :returns: the expected rate of data to be received by PST Beam component.
        :rtype: float
        """
        return self._expected_data_rate

    # --------
    # Commands
    # --------
    @command(
        dtype_out=("str",),
        doc_out="Version strings",
    )
    @DebugIt()
    def GetVersionInfo(self: PstBeam) -> List[str]:
        """
        Return the version information of the device.

        :return: The result code and the command unique ID
        """
        return [f"{self.__class__.__name__}, {self._build_state}"]

    def _update_admin_mode(self: PstBeam, admin_mode: AdminMode) -> None:
        super()._update_admin_mode(admin_mode)
        if hasattr(self, "component_manager"):
            self.component_manager.update_admin_mode(admin_mode)


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
    return run((PstBeam,), args=args, **kwargs)


if __name__ == "__main__":
    main()
