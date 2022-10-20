# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides the base Component Manager fror PST.LMC."""

from __future__ import annotations

import functools
import logging
from threading import Event
from typing import Any, Callable, Optional, Tuple

from ska_tango_base.base import TaskExecutorComponentManager, check_communicating
from ska_tango_base.control_model import CommunicationStatus, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus
from ska_tango_base.subarray import SubarrayComponentManager

from ska_pst_lmc.component.process_api import PstProcessApi
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor

__all__ = [
    "PstApiComponentManager",
    "PstComponentManager",
    "TaskResponse",
]


TaskResponse = Tuple[TaskStatus, str]


class PstComponentManager(TaskExecutorComponentManager, SubarrayComponentManager):
    """
    Base Component Manager for the PST.LMC. subsystem.

    This base class is used to provide the common functionality of the
    PST Tango components, such as providing the the communication with
    processes that are running (i.e. RECV, DSP, or SMRB).

    This class also helps abstract away calling out to whether we're
    using a simulated process or a real subprocess.
    """

    _simuation_mode: SimulationMode

    def __init__(
        self: PstComponentManager,
        device_name: str,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        *args: Any,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This
            is used within the gRPC process to identify who is
            doing the calling.
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        self._device_name = device_name
        self._simuation_mode = simulation_mode
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
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
        return self._simuation_mode

    @simulation_mode.setter
    def simulation_mode(self: PstComponentManager, simulation_mode: SimulationMode) -> None:
        """Set simulation mode state.

        :param simulation_mode: the new simulation mode value.
        :type simulation_mode: :py:class:`SimulationMode`
        """
        if self._simuation_mode != simulation_mode:
            self._simuation_mode = simulation_mode
            self._simulation_mode_changed()

    def _simulation_mode_changed(self: PstComponentManager) -> None:
        """Handle change of simulation mode.

        Default implementation of this is to do nothing. It is up to the individual devices
        to handle what it means when the simulation mode changes.
        """

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

        def _task(
            *args: Any,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            self._component_state_callback(power=PowerState.OFF)
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    @check_communicating
    def standby(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Put the component into low-power standby mode.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            self._component_state_callback(power=PowerState.STANDBY)
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)

        return self.submit_task(_task, task_callback=task_callback)

    @check_communicating
    def on(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            self._component_state_callback(power=PowerState.ON)
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    @check_communicating
    def reset(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Reset the component (from fault state).

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            self._component_state_callback(fault=False, power=PowerState.OFF)
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)

        return self.submit_task(_task, task_callback=task_callback)

    def obsreset(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Reset the component to unconfigured but do not release resources."""

        def _task(
            *args: Any,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            self._component_state_callback(configured=False)
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)

        return self.submit_task(_task, task_callback=task_callback)

    def restart(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure and release all resources."""

        def _task(
            *args: Any,
            task_callback: Optional[Callable] = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            if task_callback:
                task_callback(status=TaskStatus.IN_PROGRESS)
            self._component_state_callback(configured=False, resourced=False)
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)

        return self.submit_task(_task, task_callback=task_callback)

    def go_to_fault(self: PstComponentManager, task_callback: Callable) -> TaskResponse:
        """Set the component into a FAULT state.

        For BEAM this will make the sub-devices be put into a FAULT state. For
        API backed component managers it is expected that the service backing that
        API should be put into a FAULT state.
        """
        raise NotImplementedError("PstComponentManager is abstract class")


class PstApiComponentManager(PstComponentManager):
    """
    A base component Manager for the PST.LMC. that uses and API.

    Instances of this component manager are required to provide an
    instance of :py:class::`PstProcessApi` to delegate functionality
    to.

    Only components that use an external process, such as RECV and SMRB
    are to be extended from this class. Components such as BEAM need
    to use :py:class::`PstComponentManager` as they don't use a process
    API.
    """

    def __init__(
        self: PstApiComponentManager,
        device_name: str,
        api: PstProcessApi,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This
            is used within the gRPC process to identify who is
            doing the calling.
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param api: an API object used to delegate functionality to.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        self._api = api
        super().__init__(
            device_name, logger, communication_state_callback, component_state_callback, *args, **kwargs
        )

    def _handle_communication_state_change(
        self: PstApiComponentManager, communication_state: CommunicationStatus
    ) -> None:
        """Handle change in communication state."""
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            self._connect_to_api()
        elif communication_state == CommunicationStatus.DISABLED:
            self._disconnect_from_api()

    def _connect_to_api(self: PstApiComponentManager) -> None:
        """Establish connection to API component."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._api.connect()
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._component_state_callback(fault=None, power=PowerState.OFF)

    def _disconnect_from_api(self: PstApiComponentManager) -> None:
        """Establish connection to API component."""
        self._api.disconnect()
        self._update_communication_state(CommunicationStatus.DISABLED)
        self._component_state_callback(fault=None, power=PowerState.UNKNOWN)

    def _simulation_mode_changed(self: PstApiComponentManager) -> None:
        """Handle change of simulation mode."""
        curr_communication_state = self.communication_state
        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.debug(
                f"{self._device_name} simulation mode changed while "
                + "communicating so stopping communication."
            )
            self.stop_communicating()

        self._update_api()

        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.debug(
                f"{self._device_name} simulation mode changed while "
                + "communicating so restarting communication."
            )
            self.start_communicating()

    def _update_api(self: PstApiComponentManager) -> None:
        """Update API used by component manager.

        This is called when there is a change in the simulation mode.
        """
        raise NotImplementedError("PstApiComponentManager is abstract.")

    def assign(self: PstApiComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """
        self._api.configure_beam(resources, task_callback)
        return TaskStatus.QUEUED, "Resourcing"

    def release(self: PstApiComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Release resources from the component.

        This will release all the resources for this component, due to the fact that in PST it
        does not make sense that a BEAM can be partially configured. It's either all or nothing.

        :param resources: resources to be released
        """
        # pylint: disable=unused-argument
        return self.release_all(task_callback=task_callback)

    def release_all(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """Release all resources."""
        return self._submit_background_task(self._api.deconfigure_beam, task_callback=task_callback)

    def configure(self: PstApiComponentManager, configuration: dict, task_callback: Callable) -> TaskResponse:
        """
        Configure the component.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        return self._submit_background_task(
            functools.partial(self._api.configure_scan, configuration=configuration),
            task_callback=task_callback,
        )

    def deconfigure(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure this component."""
        return self._submit_background_task(self._api.deconfigure_scan, task_callback=task_callback)

    def scan(self: PstApiComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""
        # should be for how long the scan is and update based on that.
        return self._submit_background_task(
            functools.partial(self._api.start_scan, args), task_callback=task_callback
        )

    def end_scan(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""
        return self._submit_background_task(self._api.stop_scan, task_callback=task_callback)

    def abort(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """Abort current process.

        The only long lived process for API based devices is that of SCANNING. However,
        if another system fails this can be used to put all the subsystems into an ABORTED
        state.
        """
        self._api.abort(task_callback=task_callback)
        return TaskStatus.IN_PROGRESS, "Aborting"

    def obsreset(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """Reset service.

        This is used to reset a service in ABORTED or FAULT states back to an IDLE state.
        This will deconfigure a scan if already configured but will keep the assigned
        resources.
        """
        return self._submit_background_task(self._api.reset, task_callback=task_callback)

    def restart(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """Restart service.

        This is used to reset a service in ABORTED or FAULT states back to an EMPTY state.
        This will deconfigure a scan and release all the resources the service has.
        """
        return self._submit_background_task(self._api.restart, task_callback=task_callback)

    def go_to_fault(self: PstApiComponentManager, task_callback: Callable) -> TaskResponse:
        """Put the service into a FAULT state."""

        def _task(
            *args: Any, task_callback: Callable, task_abort_event: Optional[Event] = None, **kwargs: Any
        ) -> None:

            task_callback(status=TaskStatus.IN_PROGRESS)
            self._api.go_to_fault()
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_background_task(_task, task_callback=task_callback)

    def _submit_background_task(
        self: PstApiComponentManager, task: Callable, task_callback: Callable
    ) -> TaskResponse:
        def _task(
            *args: Any,
            task_callback: Callable,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            task(task_callback=task_callback)

        return self.submit_task(_task, task_callback=task_callback)
