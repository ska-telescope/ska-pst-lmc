# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for the base Tango device used in PST.LMC."""

from __future__ import annotations

import tango
from ska_tango_base import SKASubarray
from ska_tango_base.control_model import ObsState, SimulationMode
from tango.server import attribute

__all__ = ["PstBaseDevice"]


class PstBaseDevice(SKASubarray):
    """Base class for all the TANGO devices in PST.LMC."""

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstBaseDevice) -> None:
        """Initialise the attributes and properties of the PstReceive.

        This overrides the :py:class:`SKABaseDevice`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()

    def always_executed_hook(self: PstBaseDevice) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstBaseDevice) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    # ----------
    # Attributes
    # ----------
    @attribute(
        dtype=SimulationMode,
        memorized=True,
        hw_memorized=True,
    )
    def simulationMode(self: PstBaseDevice):
        """
        Report the simulation mode of the device.

        :return: the current simulation mode
        """
        return self.component_manager.simulation_mode

    @simulationMode.write  # type: ignore[no-redef]
    def simulationMode(self: PstBaseDevice, value: SimulationMode) -> None:
        """
        Set the simulation mode.

        :param value: The simulation mode, as a SimulationMode value
        """
        if self._obs_state == ObsState.EMPTY:
            self.component_manager.simulation_mode = value
            self.push_change_event("simulationMode", value)
            self.push_archive_event("simulationMode", value)
        else:
            self.logger.warning(
                f"Attempt to set simulation mode when not in EMPTY state. Current state is {self._obs_state}"
            )
            raise ValueError("Unable to change simulation mode unless in EMPTY observation state")
