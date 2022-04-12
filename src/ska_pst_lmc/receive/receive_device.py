# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the RECV capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import List, Optional

import tango
from ska_tango_base.control_model import SimulationMode
from ska_tango_base.subarray import SKASubarray
from tango import DebugIt
from tango.server import attribute, command, run

import ska_pst_lmc.release as release
from ska_pst_lmc.receive.receive_component_manager import PstReceiveComponentManager

__all__ = ["PstReceive", "main"]


class PstReceive(SKASubarray):
    """A software TANGO device for managing the RECV component of the PST.LMC subsystem."""

    # -----------------
    # Device Properties
    # -----------------

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

    def create_component_manager(
        self: PstReceive,
    ) -> PstReceiveComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstReceiveComponentManager(
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def always_executed_hook(self: PstReceive) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstReceive) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevFloat",
        unit="Gigabits per second",
        standard_unit="Gigabits per second",
        display_unit="Gb/s",
        polling_period=5000,
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
        polling_period=5000,
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
        polling_period=5000,
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
        polling_period=5000,
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
        polling_period=5000,
        doc="The total number of packets received out of order in the current scan",
    )
    def misordered_packets(self: PstReceive) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self.component_manager.misordered_packets

    @attribute(
        dtype="DevULong64",
        polling_period=5000,
        doc="Total number of malformed packets received during the current scan",
    )
    def malformed_packets(self: PstReceive) -> int:
        """Get the total number of malformed packets received during the current scan.

        :returns: total number of malformed packets received during the current scan.
        :rtype: int
        """
        return self.component_manager.malformed_packets

    @attribute(
        dtype="DevFloat",
        polling_period=5000,
        doc="Time average of all relative weights for the current scan",
    )
    def relative_weight(self: PstReceive) -> float:
        """Get the time averages of all relative weights for the current scan.

        :returns: time average of all relative weights for the current scan.
        :rtype: float
        """
        return self.component_manager.relative_weight

    @attribute(
        dtype=("DevFloat",),
        max_dim_x=1024,
        polling_period=5000,
        min_value=0,
        doc="Time average of relative weights for each channel in the current scan",
    )
    def relative_weights(self: PstReceive) -> List[float]:
        """Get the time average of relative weights for each channel in the current scan.

        :returns: time average of relative weights for each channel in the current scan.
        :rtype: list(float)
        """
        return self.component_manager.relative_weights

    @attribute(
        dtype=SimulationMode,
        memorized=True,
        hw_memorized=True,
    )
    def simulationMode(self: PstReceive) -> SimulationMode:
        """
        Report the simulation mode of the device.

        :return: the current simulation mode
        """
        return self.component_manager.simulation_mode

    @simulationMode.write  # type: ignore[no-redef]
    def simulationMode(self: PstReceive, value: SimulationMode) -> None:
        """
        Set the simulation mode.

        :param value: The simulation mode, as a SimulationMode value
        """
        self.component_manager.simulation_mode = value

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
        return [f"{self.__class__.__name__}, {self.read_buildState()}"]

    # --------
    # Commands
    # --------


# ----------
# Run server
# ----------


def main(args: Optional[list] = None, **kwargs: dict) -> int:
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
