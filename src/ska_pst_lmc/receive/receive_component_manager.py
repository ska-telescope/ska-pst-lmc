# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the base PST component manager."""

# TODO - expose the properties that the RECV device needs
#     - this will need to update the stats on given period

from __future__ import annotations

import logging
import time
from typing import Any, Callable, List, Optional, Tuple

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import PstComponentManager
from ska_pst_lmc.receive.receive_simulator import PstReceiveSimulator
from ska_pst_lmc.util.background_task import BackgroundTask

TaskResponse = Tuple[TaskStatus, str]


class PstReceiveComponentManager(PstComponentManager):
    """Component manager for the RECV component for the PST.LMC subsystem."""

    _received_data: int = 0
    _received_rate: float = 0.0
    _dropped_data: int = 0
    _dropped_rate: float = 0.0
    _nchan: int = 0
    _misordered_packets: int = 0
    _malformed_packets: int = 0
    _relative_weights: List[float] = []
    _relative_weight: float = 0.0

    _simulator: PstReceiveSimulator
    _communication_task: Optional[BackgroundTask] = None

    def __init__(
        self: PstReceiveComponentManager,
        simulation_mode: SimulationMode,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool, PowerState], None],
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
        self._simulator = PstReceiveSimulator()
        super().__init__(
            simulation_mode,
            logger,
            communication_state_callback,
            component_state_callback,
            *args,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

    def __del__(self: PstReceiveComponentManager) -> None:
        """Deconstruct object.

        This will make sure that if there is a background task running
        that it is stopped.
        """
        if self._communication_task is not None:
            self._communication_task.stop()

    def _handle_communication_state_change(
        self: PstReceiveComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            self._connect_to_receive()
        elif communication_state == CommunicationStatus.DISABLED:
            self._disconnect_from_receive()

    def _connect_to_receive(self: PstReceiveComponentManager) -> None:
        """Establish connection to RECV component."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        if self._simuation_mode == SimulationMode.TRUE:
            self._communication_task = BackgroundTask(
                action_fn=self._monitor_action,
                logger=self.logger,
                frequency=1.0,
            )
            self._communication_task.run()
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._component_state_callback(fault=None, power=PowerState.OFF)

    def _disconnect_from_receive(self: PstReceiveComponentManager) -> None:
        if self._communication_task is not None:
            try:
                self._communication_task.stop()
            except Exception as e:
                self.logger.warning("Error while shutting down communication", e)

        self._update_communication_state(CommunicationStatus.DISABLED)
        self._component_state_callback(fault=None, power=PowerState.UNKNOWN)

    def _monitor_action(self: PstReceiveComponentManager) -> None:
        """Monitor RECV process to get the telemetry information."""
        data = self._simulator.get_data()

        self._received_data = data.received_data
        self._received_rate = data.received_rate
        self._dropped_data = data.dropped_data
        self._dropped_rate = data.dropped_rate
        self._malformed_packets = data.malformed_packets
        self._misordered_packets = data.misordeded_packets
        self._relative_weight = data.relative_weight
        self._relative_weights = data.relative_weights

    @property
    def received_rate(self: PstReceiveComponentManager) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return self._received_rate

    @property
    def received_data(self: PstReceiveComponentManager) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return self._received_data

    @property
    def dropped_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return self._dropped_rate

    @property
    def dropped_data(self: PstReceiveComponentManager) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return self._dropped_data

    @property
    def misordered_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return self._misordered_packets

    @property
    def malformed_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of malformed packets received during the current scan.

        :returns: total number of malformed packets received during the current scan.
        :rtype: int
        """
        return self._malformed_packets

    @property
    def relative_weight(self: PstReceiveComponentManager) -> float:
        """Get the time averages of all relative weights for the current scan.

        :returns: time average of all relative weights for the current scan.
        :rtype: float
        """
        return self._relative_weight

    @property
    def relative_weights(self: PstReceiveComponentManager) -> List[float]:
        """Get the time average of relative weights for each channel in the current scan.

        :returns: time average of relative weights for each channel in the current scan.
        :rtype: list(float)
        """
        return self._relative_weights

    # ---------------
    # Commands
    # ---------------

    @check_communicating
    def off(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(power=PowerState.OFF)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Power off"

    @check_communicating
    def standby(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Put the component into low-power standby mode.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(power=PowerState.STANDBY)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Device in standby"

    @check_communicating
    def on(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(power=PowerState.ON)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Power on"

    @check_communicating
    def reset(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Reset the component (from fault state).

        :param task_callback: callback to be called when the status of
            the command changes
        """
        self._component_state_callback(fault=False, power=PowerState.OFF)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Device reset"

    def assign(self: PstReceiveComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
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

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Resourcing"

    def release(self: PstReceiveComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Release resources from the component.

        :param resources: resources to be released
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            time.sleep(0.1)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Releasing"

    def release_all(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """Release all resources."""

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            time.sleep(0.1)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Releasing all"

    def configure(
        self: PstReceiveComponentManager, configuration: dict, task_callback: Callable
    ) -> TaskResponse:
        """
        Configure the component.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            self._simulator.configure(configuration=configuration)
            time.sleep(0.1)
            self._component_state_callback(configured=True)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Releasing all"

    def deconfigure(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure this component."""

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            time.sleep(0.1)
            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Deconfiguring"

    def scan(self: PstReceiveComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""
        # should be for how long the scan is and update based on that.
        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            self._simulator.scan()
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Scanning"

    def end_scan(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            task_callback(progress=66)
            self._simulator.end_scan()
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "End scanning"

    def abort(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""

        def _task() -> None:
            task_callback(status=TaskStatus.IN_PROGRESS)
            time.sleep(0.1)
            task_callback(progress=33)
            time.sleep(0.1)
            self._simulator.end_scan()
            self._component_state_callback(scanning=False)
            task_callback(progress=66)
            task_callback(status=TaskStatus.COMPLETED)

        task = BackgroundTask(
            action_fn=_task,
            logger=self.logger,
        )
        task.run()
        return TaskStatus.QUEUED, "Aborting"

    def obsreset(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """Reset the component to unconfigured but do not release resources."""
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._component_state_callback(configured=False)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Done"

    def restart(self: PstReceiveComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure and release all resources."""
        task_callback(status=TaskStatus.IN_PROGRESS)
        self._component_state_callback(configured=False, resourced=False)
        task_callback(status=TaskStatus.COMPLETED)
        return TaskStatus.QUEUED, "Done"
