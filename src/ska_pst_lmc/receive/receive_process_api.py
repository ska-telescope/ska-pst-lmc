# -*- coding: utf-8 -*-
#
# This file is part of the PstReceive project
#
#
#
# Distributed under the terms of the BSD3 license.
# See LICENSE.txt for more info.

"""Module for providing the API to be communicate with the RECV process.

This API is not a part of the component manager, as the component manager
is also concerned with callbacks to the TANGO device and has state model
management. This API is expected to be used to call to an external process
or be simulated. Most of the API is taken from the component manager.
For specifics of the API see
https://developer.skao.int/projects/ska-tango-base/en/latest/api/subarray/component_manager.html

The :py:class:`PstReceiveProcessApiSimulator` is used in testing or
simulation, for now its not run as a separate process but in future
it should be able to be set up as a separate process and the API
will call via the same mechanism that would be for the real API (i.e.
via TCP/UDP sockets.)
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator
from ska_pst_lmc.util.background_task import BackgroundTask, BackgroundTaskProcessor


class PstReceiveProcessApi:
    """Abstract class for the API of the RECV process."""

    def connect(self: PstReceiveProcessApi) -> None:
        """Connect to the external process."""
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def disconnect(self: PstReceiveProcessApi) -> None:
        """Disconnect from the external process."""
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def assign_resources(self: PstReceiveProcessApi, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def release(self: PstReceiveProcessApi, resources: dict, task_callback: Callable) -> None:
        """Release resources.

        :param resources: dictionary of resources to release.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def release_all(self: PstReceiveProcessApi, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def configure(self: PstReceiveProcessApi, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def deconfigure(self: PstReceiveProcessApi, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def scan(self: PstReceiveProcessApi, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def end_scan(self: PstReceiveProcessApi, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    def abort(self: PstReceiveProcessApi, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")

    @property
    def monitor_data(self: PstReceiveProcessApi) -> ReceiveData:
        """Get the current monitoring data.

        If the process is not scanning this needs to return an default
        :py:class:`ReceiveData` so that the client does not need to know
        the default vaules.

        :returns: current monitoring data.
        """
        raise NotImplementedError("PstReceiveProcessApi is abstract class")


class PstReceiveProcessApiSimulator(PstReceiveProcessApi):
    """A simulator implemenation version of the  API of `PstReceiveProcessApi`."""

    def __init__(
        self: PstReceiveProcessApiSimulator,
        simulator: PstReceiveSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
    ) -> None:
        """Initialise the API.

        :param simulator: the simulator instance to use in the API.
        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        """
        self._simulator = simulator
        self._logger = logger
        self._component_state_callback = component_state_callback
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self._communication_task: Optional[BackgroundTask] = None
        self.data: Optional[ReceiveData] = None

    def connect(self: PstReceiveProcessApiSimulator) -> None:
        """Connect to the external process."""
        self._communication_task = self._background_task_processor.submit_task(
            action_fn=self._monitor_action,
            frequency=1.0,
        )

    def disconnect(self: PstReceiveProcessApiSimulator) -> None:
        """Disconnect from the external process."""
        if self._communication_task is not None:
            try:
                self._communication_task.stop()
                self._communication_task = None
            except Exception as e:
                self._logger.warning("Error while shutting down communication", e)

    def assign_resources(
        self: PstReceiveProcessApiSimulator, resources: dict, task_callback: Callable
    ) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            time.sleep(0.1)
            self._component_state_callback(resourced=True)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def release(self: PstReceiveProcessApiSimulator, resources: dict, task_callback: Callable) -> None:
        """Release resources.

        :param resources: dictionary of resources to release.
        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=42)
            time.sleep(0.1)
            task_callback(progress=75)
            time.sleep(0.1)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def release_all(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=50)
            time.sleep(0.1)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def configure(self: PstReceiveProcessApiSimulator, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=30)
            time.sleep(0.1)
            task_callback(progress=60)
            self._simulator.configure(configuration=configuration)
            time.sleep(0.1)
            self._component_state_callback(configured=True)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def deconfigure(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=31)
            time.sleep(0.1)
            task_callback(progress=89)
            time.sleep(0.1)
            self._simulator.deconfigure()
            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def scan(self: PstReceiveProcessApiSimulator, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=27)
            time.sleep(0.1)
            task_callback(progress=69)
            self._simulator.scan(args)
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def end_scan(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=32)
            time.sleep(0.1)
            task_callback(progress=88)
            self._simulator.end_scan()
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    def abort(self: PstReceiveProcessApiSimulator, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=60)
            self._component_state_callback(scanning=False)
            self._simulator.abort()
            task_callback(status=TaskStatus.COMPLETED)

        self._background_task_processor.submit_task(_task)

    @property
    def monitor_data(self: PstReceiveProcessApiSimulator) -> ReceiveData:
        """Get the current monitoring data.

        :returns: current monitoring data.
        """
        return self.data or ReceiveData.defaults()

    def _monitor_action(self: PstReceiveProcessApiSimulator) -> None:
        """Monitor RECV process to get the telemetry information."""
        self.data = self._simulator.get_data()
