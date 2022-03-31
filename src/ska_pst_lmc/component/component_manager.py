# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides the base Component Manager fror PST.LMC"""

__all__ = [
    'PstComponentManager'
]

import logging
from typing import Any, Callable, Optional
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_base.base import BaseComponentManager, check_communicating


class PstComponentManager(BaseComponentManager):
    """
    Base Component Manager for the PST.LMC. subsystem.

    This base class is used to provide the common functionality of the
    PST Tango components, such as providing the the communication with
    processes that are running (i.e. RECV, DSP, or SMRB).

    This class also helps abstract away calling out to whether we're
    using a simulated process or a real subprocess.
    """

    def __init__(self,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool], None],
        *args: Any,
        **kwargs: Any
    ):
        super().__init__(logger, communication_state_callback, component_state_callback, **args)

    def start_communicating(self):
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

    def stop_communicating(self):
        """
        Cease monitoring the component, and break off all communication with it.

        For example,

        * If you are communicating over a connection, disconnect.
        * If you have subscribed to events, unsubscribe.
        * If you are running a polling loop, stop it.
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def off(self, task_callback: Callable):
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def standby(self, task_callback: Callable):
        """
        Put the component into low-power standby mode.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def on(self, task_callback: Callable):
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    @check_communicating
    def reset(self, task_callback: Callable):
        """
        Reset the component (from fault state).

        :param task_callback: callback to be called when the status of
            the command changes
        """
        raise NotImplementedError("PstComponentManager is abstract.")
