# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for the base Tango device used in PST.LMC."""

from __future__ import annotations

import functools
from typing import Any, Callable, Generic, Optional, TypeVar, cast

import tango
from ska_tango_base import SKASubarray
from ska_tango_base.base import BaseComponentManager
from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.control_model import ObsState, SimulationMode
from tango import DebugIt
from tango.server import attribute, command

from ska_pst_lmc.component.component_manager import PstComponentManager

__all__ = ["PstBaseDevice"]

T = TypeVar("T", bound=PstComponentManager)
"""Create a generic type for the component manager.

Doing this allows us to cast the component manager used
in the base to have the correct type and allow for tools
like `mypy <http://mypy-lang.org/>`_ to check if there are
errors.
"""


class PstBaseDevice(Generic[T], SKASubarray):
    """Base class for all the TANGO devices in PST.LMC.

    This extends from :py:class:`SKASubarray` but is also
    generic in the type of the component manager.
    """

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

    def init_command_objects(self: PstBaseDevice) -> None:
        """Set up the command objects."""
        super().init_command_objects()

        def _callback(hook: Callable, running: bool) -> None:
            action = "invoked" if running else "completed"
            self.obs_state_model.perform_action(f"{hook}_{action}")

        self.register_command_object(
            "GoToFault",
            SubmittedSlowCommand(
                "GoToFault",
                self._command_tracker,
                self.component_manager,
                "go_to_fault",
                callback=None,
                logger=None,
            ),
        )

        self.register_command_object(
            "AssignResources",
            SubmittedSlowCommand(
                "AssignResources",
                self._command_tracker,
                self.component_manager,
                "configure_beam",
                callback=functools.partial(_callback, "assign"),
            ),
        )

        self.register_command_object(
            "ReleaseAllResources",
            SubmittedSlowCommand(
                "ReleaseAllResources",
                self._command_tracker,
                self.component_manager,
                "deconfigure_beam",
                callback=functools.partial(_callback, "release"),
            ),
        )

        self.register_command_object(
            "ReleaseResources",
            SubmittedSlowCommand(
                "ReleaseAllResources",
                self._command_tracker,
                self.component_manager,
                "deconfigure_beam",
                callback=functools.partial(_callback, "release"),
            ),
        )

        self.register_command_object(
            "Scan",
            SubmittedSlowCommand(
                "Scan",
                self._command_tracker,
                self.component_manager,
                "start_scan",
            ),
        )

    def always_executed_hook(self: PstBaseDevice) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstBaseDevice) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    def create_component_manager(self: PstBaseDevice) -> T:
        """
        Create and return a component manager for this device.

        :raises NotImplementedError: for no implementation
        """
        raise NotImplementedError(
            "PstBaseDevice is abstract; implement 'create_component_manager` method in " "a subclass.`"
        )

    def _component_state_changed(  # type: ignore[override]
        self: PstBaseDevice,
        obsfault: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """
        Handle change in this device's state.

        This overrides the `ska_tango_base.SKASubarray` method to allow
        for handling of when the device goes into a fault state.

        :param obsfault: whether there is a fault. If set to true this
            will put the system into a FAULT state.
        """
        super()._component_state_changed(**kwargs)

        if obsfault is not None:
            if obsfault:
                self.obs_state_model.perform_action("component_obsfault")

    @property  # type: ignore[override]
    def component_manager(self: PstBaseDevice) -> T:  # type: ignore[override]
        """Get component manager.

        Overrides the super class property of component_manager to be typesafe.

        :returns: the component manager casted to type T.
        """
        return cast(T, self._component_manager)

    @component_manager.setter
    def component_manager(self: PstBaseDevice, component_manager: BaseComponentManager) -> None:
        self._component_manager = component_manager

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
            self._simulation_mode = value
            self.push_change_event("simulationMode", value)
            self.push_archive_event("simulationMode", value)
            self.component_manager.simulation_mode = value
        else:
            self.logger.warning(
                f"Attempt to set simulation mode when not in EMPTY state. Current state is {self._obs_state}"
            )
            raise ValueError("Unable to change simulation mode unless in EMPTY observation state")

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="([Command ResultCode], [Unique ID of the command])",
    )
    @DebugIt()
    def GoToFault(self: PstBaseDevice) -> Any:
        """Put the device and sub-devices and services into a FAULT state.

        This is implemented as a long running command as a service may take some
        time to respond.

        :return: A tuple containing a result code and the unique ID of the command
        :rtype: ([ResultCode], [str])
        """
        handler = self.get_command_object("GoToFault")
        (result_code, message) = handler()
        return [[result_code], [message]]
