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
from ska_pst_lmc.component.pst_device import PstBaseProccesDevice
from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager
from ska_pst_lmc.receive.receive_model import ReceiveData

__all__ = ["PstReceive", "main"]


class PstReceive(PstBaseProccesDevice[PstReceiveComponentManager]):
    """A software TANGO device for managing the RECV component of the PST.LMC system."""

    # -----------------
    # Device Properties
    # -----------------
    process_api_endpoint = device_property(dtype=str, doc="Endpoint for the RECV.CORE service.")

    network_interface = device_property(
        dtype=str, default_value="0.0.0.0", doc="Network interface for RECV to listen on."
    )

    # the default value here is just a placeholder, this can be changed in the future.
    udp_port = device_property(dtype=int, default_value=20000, doc="The UDP port for RECV to listen on.")

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
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for f in dataclasses.fields(ReceiveData):
            self.set_change_event(f.name, True, True)
            self.set_archive_event(f.name, True)

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
            network_interface=self.network_interface,
            udp_port=self.udp_port,
            monitor_polling_rate=self.monitor_polling_rate,
            monitor_data_callback=self._update_monitor_data,
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
            self.push_change_event(key, value)
            self.push_archive_event(key, value)

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevFloat",
        unit="Gigabits per second",
        standard_unit="Gigabits per second",
        display_unit="Gb/s",
        max_value=200,
        min_value=0,
        doc="Current data receive rate from the CBF interface",
    )
    def received_rate(self: PstReceive) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self.component_manager.received_rate

    @attribute(
        dtype="DevULong64",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total number of bytes received from the CBF in the current scan",
    )
    def received_data(self: PstReceive) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self.component_manager.received_data

    @attribute(
        dtype="DevFloat",
        label="Drop Rate",
        unit="Megabits per second",
        standard_unit="Megabits per second",
        display_unit="MB/s",
        max_value=200,
        min_value=-1,
        max_alarm=10,
        min_alarm=-1,
        max_warning=1,
        min_warning=-1,
        doc="Current rate of CBF ingest data being dropped or lost by the receiving process",
    )
    def dropped_rate(self: PstReceive) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return self.component_manager.dropped_rate

    @attribute(
        dtype="DevULong64",
        label="Dropped",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Total number of bytes dropped in the current scan",
    )
    def dropped_data(self: PstReceive) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return self.component_manager.dropped_data

    @attribute(
        dtype="DevULong64",
        label="Out of order packets",
        doc="The total number of packets received out of order in the current scan",
    )
    def misordered_packets(self: PstReceive) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self.component_manager.misordered_packets

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
