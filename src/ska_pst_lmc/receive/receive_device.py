# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the RECV.MGMT capability for the Pulsar Timing Sub-element."""

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
from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager
from ska_pst_lmc.receive.receive_model import ReceiveData

__all__ = ["PstReceive", "main"]


class PstReceive(PstBaseProcessDevice[PstReceiveComponentManager]):
    """A software TANGO device for managing the RECV component of the PST.LMC system."""

    # -----------------
    # Device Properties
    # -----------------
    process_api_endpoint = device_property(dtype=str, doc="Endpoint for the RECV.CORE service.")

    subband_udp_ports = device_property(
        dtype=(int,), default_value=[20000], doc="The UDP ports for RECV subbands to listen on."
    )

    monitor_polling_rate = device_property(
        dtype=int, default_value=5000, doc="Rate at which monitor polling should happen, in milliseconds."
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstReceive) -> None:
        """Initialise the attributes and properties of the PstReceive.

        This overrides the :py:class:`SKABaseDevice`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()

        self._received_rate = 0.0
        self._received_data = 0
        self._dropped_rate = 0.0
        self._dropped_data = 0
        self._misordered_packets = 0

        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for f in dataclasses.fields(ReceiveData):
            attr_name = as_device_attribute_name(f.name)
            self.set_change_event(attr_name, True, False)
            self.set_archive_event(attr_name, True, False)

        self.set_change_event("subbandBeamConfiguration", True, False)
        self.set_archive_event("subbandBeamConfiguration", True, False)

    def create_component_manager(
        self: PstReceive,
    ) -> PstReceiveComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstReceiveComponentManager(
            device_name=self.get_name(),
            process_api_endpoint=self.process_api_endpoint,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            subband_udp_ports=self.subband_udp_ports,
            monitor_polling_rate=self.monitor_polling_rate,
            monitor_data_callback=self._update_monitor_data,
            beam_id=self.DeviceID,
            property_callback=self._update_attribute_value,
        )

    def always_executed_hook(self: PstReceive) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstReceive) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    def _update_monitor_data(self: PstReceive, data: ReceiveData) -> None:
        for (key, value) in dataclasses.asdict(data).items():
            self._update_attribute_value(key, value)

    def _update_attribute_value(self: PstReceive, key: str, value: Any) -> None:
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
        dtype=float,
        unit="Bytes per second",
        standard_unit="Bytes per second",
        display_unit="B/s",
        max_value=200,
        min_value=0,
        doc="Current data receive rate from the CBF interface",
    )
    def receivedRate(self: PstReceive) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in B/s.
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
    def receivedData(self: PstReceive) -> int:
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
    def droppedRate(self: PstReceive) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in B/s.
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
    def droppedData(self: PstReceive) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan.
        :rtype: int
        """
        return self._dropped_data

    @attribute(
        dtype=int,
        label="Out of order packets",
        doc="The total number of packets received out of order in the current scan",
    )
    def misorderedPackets(self: PstReceive) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self._misordered_packets

    @attribute(
        dtype=str,
        label="Data receive IP address.",
        doc="The IP address that PST RECV is listening for data.",
    )
    def dataReceiveIpAddress(self: PstReceive) -> str:
        """Get the data receive IP address.

        It is only valid to call this method when the Tango device is turned on
        and communicating.
        """
        return self.component_manager.data_host

    @attribute(
        dtype=str,
        label="The current subband beam configuration.",
        doc="Current calculated subband beam configuration.",
    )
    def subbandBeamConfiguration(self: PstReceive) -> str:
        """Get current subband beam configuration.

        Retrieves the current subband configuration that is calculated during
        the `ConfigureBeam` request. When RECV is deconfigured for beam then
        the response is an empty JSON object `{}`.

        :return: current subband beam configuration.
        :rtype: str
        """
        import json

        return json.dumps(self.component_manager.subband_beam_configuration)

    # --------
    # Commands
    # --------
    @command(
        dtype_out=("str",),
        doc_out="Version strings",
    )
    @DebugIt()
    def GetVersionInfo(self: PstReceive) -> List[str]:
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
    return run((PstReceive,), args=args, **kwargs)


if __name__ == "__main__":
    main()
