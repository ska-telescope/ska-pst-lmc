# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides the base Component Manager fror PST.LMC."""

from __future__ import annotations

import logging
from typing import Any, Callable, Tuple

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus
from ska_tango_base.subarray import SubarrayComponentManager

from ska_pst_lmc.component.process_api import PstProcessApi

__all__ = ["PstComponentManager"]


TaskResponse = Tuple[TaskStatus, str]


class PstComponentManager(SubarrayComponentManager):
    """
    Base Component Manager for the PST.LMC. subsystem.

    This base class is used to provide the common functionality of the
    PST Tango components, such as providing the the communication with
    processes that are running (i.e. RECV, DSP, or SMRB).

    This class also helps abstract away calling out to whether we're
    using a simulated process or a real subprocess.
    """

    _simuation_mode: SimulationMode = SimulationMode.TRUE

    def __init__(
        self: PstComponentManager,
        simulation_mode: SimulationMode,
        api: PstProcessApi,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialise instance of the component manager.

        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        self._simuation_mode = simulation_mode
        self._api = api
        super().__init__(logger, communication_state_callback, component_state_callback, *args, **kwargs)

    def start_communicating(self: PstComponentManager) -> None:
        """
        Establish communication with the component, then start monitoring.

        This is the place to do things like:

        * Initiate a connection to the component (if your communication
          is connection-oriented)
        * Subscribe to component events (if using "pull" model)
        * Start a polling loop to monitor the component (if using a
          "push" model)
        """
        if self._communication_state == CommunicationStatus.ESTABLISHED:
            return
        if self._communication_state == CommunicationStatus.DISABLED:
            self._handle_communication_state_change(CommunicationStatus.NOT_ESTABLISHED)

    def stop_communicating(self: PstComponentManager) -> None:
        """
        Cease monitoring the component, and break off all communication with it.

        For example,

        * If you are communicating over a connection, disconnect.
        * If you have subscribed to events, unsubscribe.
        * If you are running a polling loop, stop it.
        """
        if self._communication_state == CommunicationStatus.DISABLED:
            return

        self._handle_communication_state_change(CommunicationStatus.DISABLED)

    def _handle_communication_state_change(
        self: PstComponentManager, communication_state: CommunicationStatus
    ) -> None:
        raise NotImplementedError("PstComponentManager is abstract.")

    @property
    def simulation_mode(self: PstComponentManager) -> SimulationMode:
        """Get value of simulation mode state.

        :returns: current simulation mode state.
        """
        self._simuation_mode

    @simulation_mode.setter
    def simulation_mode(self: PstComponentManager, simulation_mode: SimulationMode) -> None:
        """Set simulation mode state.

        :param simulation_mode: the new simulation mode value.
        :type simulation_mode: :py:class:`SimulationMode`
        """
        self._simuation_mode = simulation_mode

    # ---------------
    # Commands
    # ---------------

    @check_communicating
    def off(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(power=PowerState.OFF)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Power off"

    @check_communicating
    def standby(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Put the component into low-power standby mode.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(power=PowerState.STANDBY)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Device in standby"

    @check_communicating
    def on(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(power=PowerState.ON)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Power on"

    @check_communicating
    def reset(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Reset the component (from fault state).

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(fault=False, power=PowerState.OFF)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Device reset"

    def assign(self: PstComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """
        self._api.assign_resources(resources, task_callback)
        return TaskStatus.QUEUED, "Resourcing"

    def release(self: PstComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Release resources from the component.

        :param resources: resources to be released
        """
        self._api.release(resources, task_callback)
        return TaskStatus.QUEUED, "Releasing"

    def release_all(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Release all resources."""
        self._api.release_all(task_callback)
        return TaskStatus.QUEUED, "Releasing all"

    def configure(self: PstComponentManager, configuration: dict, task_callback: Callable) -> TaskResponse:
        """
        Configure the component.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        self._api.configure(configuration, task_callback)
        return TaskStatus.QUEUED, "Releasing all"

    def deconfigure(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure this component."""
        self._api.deconfigure(task_callback)
        return TaskStatus.QUEUED, "Deconfiguring"

    def scan(self: PstComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""
        # should be for how long the scan is and update based on that.
        self._api.scan(args, task_callback)
        return TaskStatus.QUEUED, "Scanning"

    def end_scan(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""
        self._api.end_scan(task_callback)
        return TaskStatus.QUEUED, "End scanning"

    def abort(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""
        self._api.abort(task_callback)
        return TaskStatus.QUEUED, "Aborting"

    def obsreset(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Reset the component to unconfigured but do not release resources."""
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Done"

    def restart(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure and release all resources."""
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._component_state_callback(configured=False, resourced=False)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Done"
