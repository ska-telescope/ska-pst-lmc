# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the base abstract API for the PST.LMC processes.

This API is not a part of the component manager, as the component manager
is also concerned with callbacks to the TANGO device and has state model
management. This API is expected to be used to call to an external process
or be simulated. Most of the API is taken from the component manager.
For specifics of the API see
https://developer.skao.int/projects/ska-tango-base/en/latest/api/subarray/component_manager.html
"""

from __future__ import annotations

import logging
from typing import Callable


class PstProcessApi:
    """Abstract class for the API of the PST.LMC processes like RECV, SMRB, etc."""

    def __init__(
        self: PstProcessApi,
        logger: logging.Logger,
        component_state_callback: Callable,
    ) -> None:
        """Initialise the API.

        :param simulator: the simulator instance to use in the API.
        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        """
        self._logger = logger
        self._component_state_callback = component_state_callback

    def connect(self: PstProcessApi) -> None:
        """Connect to the external process."""
        raise NotImplementedError("PstProcessApi is abstract class")

    def disconnect(self: PstProcessApi) -> None:
        """Disconnect from the external process."""
        raise NotImplementedError("PstProcessApi is abstract class")

    def assign_resources(self: PstProcessApi, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def release_resources(self: PstProcessApi, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def configure(self: PstProcessApi, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def deconfigure(self: PstProcessApi, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def scan(self: PstProcessApi, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def end_scan(self: PstProcessApi, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def abort(self: PstProcessApi, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def reset(self: PstProcessApi, task_callback: Callable) -> None:
        """Reset the component.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def restart(self: PstProcessApi, task_callback: Callable) -> None:
        """Perform a restart of the component.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")
