# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for the base Tango device used in PST.LMC."""

from __future__ import annotations
import functools

import json
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, cast

import tango
from ska_tango_base.base import BaseComponentManager
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import CommandTrackerProtocol, ResultCode, SubmittedSlowCommand
from ska_tango_base.control_model import ObsState, SimulationMode
from ska_tango_base.csp import CspSubElementObsDevice
from ska_tango_base.faults import StateModelError
from ska_tango_base.obs import ObsStateModel
from tango import DebugIt
from tango.server import attribute, command

from ska_pst_lmc.component.component_manager import PstComponentManager
from ska_pst_lmc.util.callback import Callback

__all__ = ["PstBaseDevice"]

T = TypeVar("T", bound=PstComponentManager)
"""Create a generic type for the component manager.

Doing this allows us to cast the component manager used
in the base to have the correct type and allow for tools
like `mypy <http://mypy-lang.org/>`_ to check if there are
errors.
"""

class PstBaseDevice(Generic[T], CspSubElementObsDevice):
    """Base class for all the TANGO devices in PST.LMC.

    This extends from :py:class:`CspSubElementObsDevice` but is also
    generic in the type of the component manager.

    The `CspSubElementObsDevice` class is used as a base rather
    than a `SKASubarray` due to the fact this PST is a software
    subelement within CSP.
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

    # -----------
    # Commands
    # -----------

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """A class for the PstBaseDevice's ConfigureScan command.

        This class overrides the CspSubElementObsDevice.ConfigureScanCommand's
        `validate_input` method to no assert the `id` field.
        """

        def validate_input(self: PstBaseDevice.ConfigureScanCommand, argin: str) -> Tuple[Dict[str, Any], ResultCode, str]:
            """
            Validate the configuration parameters against allowed values, as needed.

            :param argin: The JSON formatted string with configuration for the device.
            :type argin: str
            :return: A tuple containing a return code and a string message.
            :rtype: (ResultCode, str)
            """
            try:
                configuration_dict: Dict[str, Any] = cast(Dict[str, Any], json.loads(argin))
            except (json.JSONDecodeError) as err:
                msg = f"Validate configuration failed with error:{err}"
                self.logger.error(msg)
                return (None, ResultCode.FAILED, msg)
            except Exception as other_errs:
                msg = f"Validate configuration failed with unknown error: {other_errs}"
                return (None, ResultCode.FAILED, msg)

            return (
                configuration_dict,
                ResultCode.OK,
                "ConfigureScan arguments validation successful",
            )

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

    def _simulation_mode_allowed_obs_states(self: PstBaseDevice) -> List[ObsState]:
        return [ ObsState.EMPTY, ObsState.IDLE]

    @simulationMode.write  # type: ignore[no-redef]
    def simulationMode(self: PstBaseDevice, value: SimulationMode) -> None:
        """
        Set the simulation mode.

        :param value: The simulation mode, as a SimulationMode value
        """
        if self._obs_state in self._simulation_mode_allowed_obs_states():
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

class PstBaseProccesDevice(Generic[T], PstBaseDevice[T]):
    """Base class for all the TANGO devices that manager an external process.

    This extends from :py:class:`PstBaseDevice` but exposes the ConfigureBeam
    method. This allows for setting up the beam related configuration that
    may not change as often as the scan configuration.
    """

    def init_command_objects(self: PstBaseDevice) -> None:
        """Set up the command objects."""
        super().init_command_objects()

        def _callback(hook: str, running: bool) -> None:
            action = "invoked" if running else "completed"
            self.obs_state_model.perform_action(f"{hook}_{action}")

        for (command_name, method_name, state_model_hook) in [
            ("ConfigureBeam", "configure_beam", "assign"),
            ("DeconfigureBeam", "deconfigure_beam", "release"),
        ]:
            callback = (
                None
                if state_model_hook is None
                else functools.partial(_callback, state_model_hook)
            )
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    callback=callback,
                    logger=None,
                ),
            )


    # ---------------
    # General methods
    # ---------------

    def _init_state_model(self: PstBaseProccesDevice) -> None:
        """Set up the state model for the device."""
        super()._init_state_model()
        self.obs_state_model = ObsStateModel(
            logger=self.logger,
            callback=self._update_obs_state,
        )

    def _component_state_changed(  # type: ignore[override]
        self: PstBaseProccesDevice,
        resourced: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """
        Handle change in this device's state.

        This overrides the `PstBaseProccesDevice` method to allow
        for handling of the process device being resourced.

        :param resourced: whether the device has been resourced or not.
            If set to true this will put the device into IDLE state.
        """
        super()._component_state_changed(**kwargs)

        if resourced is not None:
            if resourced:
                self.obs_state_model.perform_action("component_resourced")
            else:
                self.obs_state_model.perform_action("component_unresourced")

    # -----------
    # Commands
    # -----------

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """A class for the CspSubElementObsDevice's init_device() "command"."""

        def do(self: PstBaseProccesDevice.InitCommand):
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            super().do()

            # Need to put Process devices into EMPTY state, not IDLE
            self._device._obs_state = ObsState.EMPTY

            message = "PstBaseProccesDevice.InitCommand completed OK"
            return (ResultCode.OK, message)

    def is_ConfigureBeam_allowed(self: PstBaseProccesDevice) -> bool:
        """
        Return whether the `ConfigureBeam` command may be called in the current state.

        :return: whether the command may be called in the current device
            state
        :rtype: bool
        """
        # If we return False here, Tango will raise an exception that incorrectly blames
        # refusal on device state.
        # e.g. "ConfigureBeam not allowed when the device is in ON state".
        # So let's raise an exception ourselves.
        if self._obs_state not in [ObsState.EMPTY]:
            raise StateModelError(
                f"ConfigureBeam command not permitted in observation state {self._obs_state.name}"
            )
        return True

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out="A tuple containing a return code and a string message indicating status. "
        "The message is for information purpose only.",
    )
    @DebugIt()
    def ConfigureBeam(self: PstBaseProccesDevice, argin: str) -> DevVarLongStringArrayType:
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.
        :type argin: str

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        handler = self.get_command_object("ConfigureBeam")

        configuration: Dict[str, Any] = cast(Dict[str, Any], json.loads(argin))
        (result_code, message) = handler(configuration)

        return [[result_code], [message]]

    def is_DeconfigureBeam_allowed(self: PstBaseProccesDevice) -> bool:
        """
        Return whether the `DeconfigureBeam` command may be called in the current state.

        :return: whether the command may be called in the current device
            state
        :rtype: bool
        """
        # If we return False here, Tango will raise an exception that incorrectly blames
        # refusal on device state.
        # e.g. "ConfigureBeam not allowed when the device is in ON state".
        # So let's raise an exception ourselves.
        if self._obs_state not in [ObsState.IDLE]:
            raise StateModelError(
                f"DeconfigureBeam command not permitted in observation state {self._obs_state.name}"
            )
        return True


    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="([Command ResultCode], [Unique ID of the command])",
    )
    @DebugIt()
    def DeconfigureBeam(self: PstBaseProccesDevice) -> DevVarLongStringArrayType:
        """
        Deconfigure the beam for process device.

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        handler = self.get_command_object("DeconfigureBeam")

        (result_code, message) = handler()

        return [[result_code], [message]]


    def _simulation_mode_allowed_obs_states(self: PstBaseDevice) -> List[ObsState]:
        return [ ObsState.EMPTY ]
