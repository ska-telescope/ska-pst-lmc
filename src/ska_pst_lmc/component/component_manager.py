# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides the base Component Manager fror PST.LMC."""

from __future__ import annotations

import logging
from typing import Any, Callable

from ska_tango_base.base import BaseComponentManager, check_communicating
from ska_tango_base.control_model import CommunicationStatus, SimulationMode

__all__ = ["PstComponentManager"]


class PstComponentManager(BaseComponentManager):
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
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool], None],
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
        raise NotImplementedError("PstComponentManager is abstract.")

    def stop_communicating(self: PstComponentManager) -> None:
        """
        Cease monitoring the component, and break off all communication with it.

        For example,

        * If you are communicating over a connection, disconnect.
        * If you have subscribed to events, unsubscribe.
        * If you are running a polling loop, stop it.
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def off(self: PstComponentManager, task_callback: Callable) -> None:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def standby(self: PstComponentManager, task_callback: Callable) -> None:
        """
        Put the component into low-power standby mode.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def on(self: PstComponentManager, task_callback: Callable) -> None:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def reset(self: PstComponentManager, task_callback: Callable) -> None:
        """
        Reset the component (from fault state).

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")
