# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing the Beam capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, cast

import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, HealthState, SimulationMode
from ska_tango_base.executor import TaskStatus
from tango import DebugIt
from tango.server import attribute, command, device_property, run

import ska_pst_lmc.release as release
from ska_pst_lmc.beam.beam_component_manager import PstBeamComponentManager
from ska_pst_lmc.beam.beam_device_interface import PstBeamDeviceInterface
from ska_pst_lmc.component import as_device_attribute_name
from ska_pst_lmc.component.pst_device import PstBaseDevice
from ska_pst_lmc.util import Configuration

__all__ = ["PstBeam", "main"]


class PstBeam(PstBaseDevice[PstBeamComponentManager], PstBeamDeviceInterface):
    """
    A logical TANGO device representing a Beam Capability for PST.LMC.

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
        """
        Initialise the attributes and properties of the PstBeam.

        This overrides the :py:class:`SKABaseDevice`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for prop in [
            "dataReceiveRate",
            "dataReceived",
            "dataDropRate",
            "dataDropped",
            "misorderedPackets",
            "misorderedPacketRate",
            "malformedPackets",
            "malformedPacketRate",
            "misdirectedPackets",
            "misdirectedPacketRate",
            "checksumFailurePackets",
            "checksumFailurePacketRate",
            "timestampSyncErrorPackets",
            "timestampSyncErrorPacketRate",
            "seqNumberSyncErrorPackets",
            "seqNumberSyncErrorPacketRate",
            "dataRecordRate",
            "dataRecorded",
            "diskCapacity",
            "diskUsedBytes",
            "diskUsedPercentage",
            "availableDiskSpace",
            "expectedDataRecordRate",
            "availableRecordingTime",
            "ringBufferUtilisation",
            "channelBlockConfiguration",
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
            device_interface=self,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
        )

    def always_executed_hook(self: PstBeam) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstBeam) -> None:
        """
        Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the init_device method to be
        released.  This method is called by the device destructor and by the device Init command.
        """
        # stop the task executor
        self.component_manager._pst_task_executor.stop()
        super().delete_device()

    def handle_attribute_value_update(self: PstBeam, attribute_name: str, value: Any) -> None:
        """
        Handle update of a device attribute value.

        :param attribute_name: the name of the attribute to update.
        :type attribute_name: str
        :param value: the new value of the attribute to update to.
        :type value: Any
        """
        try:
            attr_key = as_device_attribute_name(attribute_name)
            self.push_change_event(attr_key, value)
            self.push_archive_event(attr_key, value)
        except Exception:
            self.logger.warning(
                f"Error in attempting to set device attribute {attribute_name}.", exc_info=True
            )

    @property
    def smrb_fqdn(self: PstBeam) -> str:
        """Get the fully qualified device name (FQDN) for the SMRB.MGMT device of this beam."""
        return self.SmrbFQDN

    @property
    def recv_fqdn(self: PstBeam) -> str:
        """Get the fully qualified device name (FQDN) for the RECV.MGMT device of this beam."""
        return self.RecvFQDN

    @property
    def dsp_fqdn(self: PstBeam) -> str:
        """Get the fully qualified device name (FQDN) for the DSP.MGMT device of this beam."""
        return self.DspFQDN

    def handle_subdevice_fault(self: PstBeam, device_fqdn: str, fault_msg: str) -> None:
        """
        Handle a fault raised from a subordinate device.

        :param device_fqdn: the fully-qualified domain name of the subordinate device.
        :type device_fqdn: str
        :param fault_msg: the fault message from the subordinate device.
        :type fault_msg: str
        """
        self._health_failure_msg = fault_msg
        self._component_state_changed(obsfault=True)
        self.update_health_state(health_state=HealthState.FAILED)

    # ----------
    # Commands
    # ----------
    class ConfigureScanCommand(PstBaseDevice.ConfigureScanCommand):
        """
        A class for the ObsDevice ConfigureScan command.

        This overrides the `PstBaseDevice` command by ensuring that
        the JSON request sent is a valid CSP JSON request of at least
        v2.3.
        """

        def validate_input(
            self: PstBeam.ConfigureScanCommand, argin: str
        ) -> Tuple[Dict[str, Any], ResultCode, str]:
            """
            Validate the input request string.

            This tries to parse JSON string via the `Configuration.from_json`
            method. That method also tries to validate the CSP JSON.
            """
            import json

            try:
                configuration = Configuration.from_json(json_str=argin)
                (result, msg) = cast(
                    PstBeamComponentManager, self._component_manager
                ).validate_configure_scan(configuration=configuration.data)
                self.logger.debug(f"validate_configure_scan return result={result} and msg={msg}")
                if not result == TaskStatus.COMPLETED:
                    return ({}, ResultCode.FAILED, msg)
            except (json.JSONDecodeError, ValueError) as err:
                msg = f"Validate configuration failed with error:{err}"
                self.logger.error(msg)
                return ({}, ResultCode.FAILED, msg)
            except Exception as err:
                msg = f"Validate configuration failed with error: {err}"
                self.logger.error(msg, exc_info=True)
                return ({}, ResultCode.FAILED, msg)

            return (
                configuration.data,
                ResultCode.OK,
                "ConfigureScan arguments validation successful",
            )

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
    def diskCapacity(self: PstBeam) -> int:
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
        doc="Used space on the disk that DSP is writing to.",
    )
    def diskUsedBytes(self: PstBeam) -> int:
        """
        Get used space on the disk that DSP is writing to.

        This is `diskCapacity - availableDiskSpace`.

        :returns: used space on the disk that DSP is writing to, in bytes.
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
    def diskUsedPercentage(self: PstBeam) -> float:
        """
        Get used space on the disk that DSP is writing to.

        This is `100.0 * (diskCapacity - availableDiskSpace)/availableDiskSpace`.

        :returns: used space on the disk that DSP is writing to as a percentage.
        :rtype: float
        """
        return self.component_manager.disk_used_percentage

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Available space on the disk that DSP is writing to.",
    )
    def availableDiskSpace(self: PstBeam) -> int:
        """
        Available space on the disk that the PST.BEAM is writing to.

        :returns: available space on the disk that PST.BEAM is writing to, in bytes.
        :rtype: int
        """
        return self.component_manager.available_disk_space

    @attribute(
        dtype=float,
        unit="Seconds",
        display_unit="s",
        min_alarm=10.0,
        min_warning=60.0,
        doc="Available time, in seconds, for writing available.",
    )
    def availableRecordingTime(self: PstBeam) -> float:
        """
        Get available time, in seconds, for writing available.

        :returns: available time, in seconds, for writing available.
        :rtype: float
        """
        return self.component_manager.available_recording_time

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
    def dataReceiveRate(self: PstBeam) -> float:
        """
        Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self.component_manager.data_receive_rate

    @attribute(
        dtype=int,
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total number of bytes received from the CBF in the current scan",
    )
    def dataReceived(self: PstBeam) -> int:
        """
        Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self.component_manager.data_received

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
    def dataDropRate(self: PstBeam) -> float:
        """
        Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in Bytes/s.
        :rtype: float
        """
        return self.component_manager.data_drop_rate

    @attribute(
        dtype=int,
        label="Dropped",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total number of bytes dropped in the current scan",
    )
    def dataDropped(self: PstBeam) -> int:
        """
        Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan.
        :rtype: int
        """
        return self.component_manager.data_dropped

    @attribute(
        dtype=float,
        label="Misordered packets",
        doc=(
            "Number of out of order UDP packets received in the current scan."
            "The UDP packets for all frequency channels of a given set of"
            "time samples that start at time t0 shall arrive before the"
            "first packet containing data sampled at time t0+2 delta_t,"
            "where delta_t is the time spanned by the set of time samples"
            "in a single packet."
        ),
    )
    def misorderedPackets(self: PstBeam) -> int:
        """
        Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self.component_manager.misordered_packets

    @attribute(
        dtype=float,
        label="Misordered packet rate",
        unit="packets/sec",
        doc="The current rate of misordered packets.",
    )
    def misorderedPacketRate(self: PstBeam) -> float:
        """
        Get the current rate of misordered packets.

        :returns: the current rate of misordered packets in packets/seconds.
        :rtype: float
        """
        return self.component_manager.misordered_packet_rate

    @attribute(
        dtype=int,
        label="Malformed packets",
        doc=(
            "Malformed packets are valid UDP packets, but where contents of"
            "the UDP payload does not conform to the specification in the"
            "CBF/PST ICD. Examples of malformation include: bad magic-word"
            "field, invalid meta-data, incorrect packet size."
        ),
    )
    def malformedPackets(self: PstBeam) -> int:
        """
        Get the total number of packets marked as malformed for current scan.

        :returns: the total number of packets marked as malformed for current scan.
        :rtype: int
        """
        return self.component_manager.malformed_packets

    @attribute(
        dtype=float,
        label="Malformed packet rate",
        unit="packets/sec",
        doc="The current rate of malformed packets.",
    )
    def malformedPacketRate(self: PstBeam) -> float:
        """
        Get current rate of malformed packets.

        :return: current rate of malformed packets in packets/seconds.
        :rtype: float
        """
        return self.component_manager.malformed_packet_rate

    @attribute(
        dtype=int,
        label="Misdirected packets",
        doc=(
            "Total number of (valid) UDP packets that were unexpectedly received."
            "Misdirection could be due to wrong ScanID, Beam ID, Network Interface"
            "or UDP port. Receiving misdirected packets is a sign that there is"
            "something wrong with the upstream configuration for the scan."
        ),
    )
    def misdirectedPackets(self: PstBeam) -> int:
        """
        Get the total number of packets as marked as misdirected for current scan.

        :returns: the total number of packets as marked as misdirected for current scan.
        :rtype: int
        """
        return self.component_manager.misdirected_packets

    @attribute(
        dtype=float,
        label="Misdirected packet rate",
        unit="packets/sec",
        doc="The current rate of misdirected packets.",
    )
    def misdirectedPacketRate(self: PstBeam) -> float:
        """
        Get the current rate of misdirected packets.

        :return: the current rate of misdirected packets in packets/seconds.
        :rtype: float
        """
        return self.component_manager.misdirected_packet_rate

    @attribute(
        dtype=int,
        label="Checksum failure packets",
        doc="Total number of packets with a UDP, IP header or CRC checksum failure.",
    )
    def checksumFailurePackets(self: PstBeam) -> int:
        """
        Get the total number of packets with checksum failures for current scan.

        :return: the total number of packets with checksum failures for current scan.
        :rtype: int
        """
        return self.component_manager.checksum_failure_packets

    @attribute(
        dtype=float,
        label="Checksum failure packet rate",
        unit="packets/sec",
        doc="The current rate of packets with checkesum failures.",
    )
    def checksumFailurePacketRate(self: PstBeam) -> float:
        """
        Get the current rate of packets with checkesum failures.

        :return: the current rate of packets with checkesum failures in packets/seconds.
        :rtype: float
        """
        return self.component_manager.checksum_failure_packet_rate

    @attribute(
        dtype=int,
        label="Timestamp sync error packets",
        doc=(
            "The number of packets received where the timestamp has become"
            "desynchronised with the packet sequence number * sampling interval"
        ),
    )
    def timestampSyncErrorPackets(self: PstBeam) -> int:
        """
        Get the total number of packets with a timestamp sync error for current scan.

        :return: the total number of packets with a timestamp sync error for current scan.
        :rtype: int
        """
        return self.component_manager.timestamp_sync_error_packets

    @attribute(
        dtype=float,
        label="Timestamp sync error packet rate",
        unit="packets/sec",
        doc="The current rate of packets with a timestamp sync error.",
    )
    def timestampSyncErrorPacketRate(self: PstBeam) -> float:
        """
        Get the current rate of packets with a timestamp sync error.

        :return: the current rate of packets with a timestamp sync error in packets/seconds.
        :rtype: float
        """
        return self.component_manager.timestamp_sync_error_packet_rate

    @attribute(
        dtype=int,
        label="Seq. number sync error packets",
        doc=(
            "The number of packets received where the packet sequence number has"
            "become desynchronised with the data rate and elapsed time."
        ),
    )
    def seqNumberSyncErrorPackets(self: PstBeam) -> int:
        """
        Get the total number of packets with a seq num sync error in current scan.

        :return: the total number of packets with a seq num sync error in current scan.
        :rtype: int
        """
        return self.component_manager.seq_number_sync_error_packets

    @attribute(
        dtype=float,
        label="Seq. number sync error packet rate",
        unit="packets/sec",
        doc="The current rate of packets with a sequence number sync error.",
    )
    def seqNumberSyncErrorPacketRate(self: PstBeam) -> float:
        """
        Get the current rate of packets with a sequence number sync error.

        :return: the current rate of packets with a sequence number sync error in packets/seconds.
        :rtype: float
        """
        return self.component_manager.seq_number_sync_error_packet_rate

    @attribute(
        dtype=float,
        unit="Bytes per second",
        display_unit="B/s",
        doc="Current rate of writing to the disk.",
    )
    def dataRecordRate(self: PstBeam) -> float:
        """
        Get current rate of writing to the disk.

        :returns: use space on the disk that PST.BEAM is writing to, in bytes.
        :rtype: float
        """
        return self.component_manager.data_record_rate

    @attribute(
        dtype=int,
        unit="Bytes",
        display_unit="B",
        doc="Number of bytes written during scan.",
    )
    def dataRecorded(self: PstBeam) -> int:
        """
        Get number of bytes written during scan.

        :returns: number of bytes written during scan.
        :rtype: int
        """
        return self.component_manager.data_recorded

    @attribute(
        dtype=str,
        doc="The channel block configuration based on scan configuration.",
    )
    def channelBlockConfiguration(self: PstBeam) -> str:
        """
        Get the channel block configuration.

        This is a JSON serialised string of the channel block configuration
        that is calculated during the `ConfigureScan` command. This
        configuration includes the following properties:

            * Number of channel blocks, between 1 and 4
            * For each channel block, the block of channel numbers
              using a range in the form of inclusive of the lower
              number and exclusive of the higher number (e.g [1, 21)
              would be a range of 20 channels starting from 1 and ending
              at channel block 20 (inclusive).
            * Channel block IPv4 address to send data to.
            * Channel block UDP port

        .. code-block:: python

            {
                "num_channel_blocks": 2,
                "channel_blocks": [
                    {
                        "data_host": "10.10.0.1",
                        "data_port": 20000,
                        "start_channel": 0,
                        "num_channels": 12,
                    },
                    {
                        "data_host": "10.10.0.1",
                        "data_port": 20001,
                        "start_channel": 12,
                        "num_channels": 10,
                    },
                ]
            }

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
        """
        Get the percentage of the ring buffer elements that are full of data.

        :returns: the percentage of the ring buffer elements that are full of data.
        :rtype: float
        """
        return self.component_manager.ring_buffer_utilisation

    @attribute(
        dtype=float,
        unit="Gigabits per second",
        display_unit="Gb/s",
        doc="Expected rate of data to be received by PST Beam component.",
    )
    def expectedDataRecordRate(self: PstBeam) -> float:
        """
        Get the expected rate of data to be received by PST Beam component.

        :returns: the expected rate of data to be received by PST Beam component.
        :rtype: float
        """
        return self.component_manager.expected_data_record_rate

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
