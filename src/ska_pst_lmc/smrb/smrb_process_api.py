# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the API to be communicate with the SMRB process.

The :py:class:`PstSmrbProcessApiSimulator` is used in testing or
simulation.)
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component.process_api import PstProcessApi
from ska_pst_lmc.smrb.smrb_model import SharedMemoryRingBufferData
from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator
from ska_pst_lmc.util.background_task import BackgroundTask, BackgroundTaskProcessor, background_task

__all__ = [
    "PstSmrbProcessApi",
    "PstSmrbProcessApiSimulator",
]


class PstSmrbProcessApi(PstProcessApi):
    """Abstract class for the API of the RECV process.

    This extends from :py:class:`PstProcessApi` but
    provides the specific method of getting the monitoring
    data.
    """

    @property
    def monitor_data(self: PstSmrbProcessApi) -> SharedMemoryRingBufferData:
        """Get the current monitoring data.

        If the process is not scanning this needs to return an default
        :py:class:`SharedMemoryRingBufferData` so that the client does
        not need to know the default vaules.

        :returns: current monitoring data.
        """
        raise NotImplementedError("PstSmrbProcessApi is abstract class")


class PstSmrbProcessApiSimulator(PstSmrbProcessApi):
    """A simulator implemenation version of the  API of `PstSmrbProcessApi`."""

    def __init__(
        self: PstSmrbProcessApiSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
        simulator: Optional[PstSmrbSimulator],
    ) -> None:
        """Initialise the API.

        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        :param simulator: the simulator instance to use in the API.
        """
        self._simulator = simulator or PstSmrbSimulator()
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self._communication_task: Optional[BackgroundTask] = None
        self.data: Optional[SharedMemoryRingBufferData] = None

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def connect(self: PstSmrbProcessApiSimulator) -> None:
        """Connect to the external process."""
        self._communication_task = self._background_task_processor.submit_task(
            action_fn=self._monitor_action,
            frequency=1.0,
        )

    def disconnect(self: PstSmrbProcessApiSimulator) -> None:
        """Disconnect from the external process."""
        if self._communication_task is not None:
            try:
                self._communication_task.stop()
                self._communication_task = None
            except Exception as e:
                self._logger.warning("Error while shutting down communication", e)

    @background_task
    def assign_resources(self: PstSmrbProcessApiSimulator, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=50)
        time.sleep(0.1)
        self._component_state_callback(resourced=True)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def release(self: PstSmrbProcessApiSimulator, resources: dict, task_callback: Callable) -> None:
        """Release resources.

        :param resources: dictionary of resources to release.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=19)
        time.sleep(0.1)
        task_callback(progress=81)
        time.sleep(0.1)
        self._component_state_callback(resourced=False)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def release_all(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=45)
        time.sleep(0.1)
        self._component_state_callback(resourced=False)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def configure(self: PstSmrbProcessApiSimulator, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=42)
        time.sleep(0.1)
        task_callback(progress=58)
        self._simulator.configure(configuration=configuration)
        time.sleep(0.1)
        self._component_state_callback(configured=True)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def deconfigure(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=20)
        time.sleep(0.05)
        task_callback(progress=50)
        time.sleep(0.05)
        task_callback(progress=80)
        time.sleep(0.1)
        self._simulator.deconfigure()
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def scan(self: PstSmrbProcessApiSimulator, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=55)
        time.sleep(0.1)
        self._simulator.scan(args)
        self._component_state_callback(scanning=True)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def end_scan(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=37)
        time.sleep(0.1)
        task_callback(progress=63)
        self._simulator.end_scan()
        self._component_state_callback(scanning=False)
        task_callback(status=TaskStatus.COMPLETED)

    @background_task
    def abort(self: PstSmrbProcessApiSimulator, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        time.sleep(0.1)
        task_callback(progress=59)
        self._component_state_callback(scanning=False)
        self._simulator.abort()
        task_callback(status=TaskStatus.COMPLETED)

    @property
    def monitor_data(self: PstSmrbProcessApiSimulator) -> SharedMemoryRingBufferData:
        """Get the current monitoring data.

        :returns: current monitoring data.
        """
        return self.data or SharedMemoryRingBufferData.defaults()

    def _monitor_action(self: PstSmrbProcessApiSimulator) -> None:
        """Monitor SMRB process to get the telemetry information."""
        self.data = self._simulator.get_data()
