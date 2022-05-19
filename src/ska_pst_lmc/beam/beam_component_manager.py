# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the BEAM PST component manager."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, List, Optional, Tuple

from ska_tango_base.control_model import AdminMode, CommunicationStatus, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component.component_manager import PstComponentManager
from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.remote_task import AggregateRemoteTask

TaskResponse = Tuple[TaskStatus, str]
RemoteTaskResponse = Tuple[List[TaskStatus], List[str]]

__all__ = [
    "PstBeamComponentManager",
]


class _PstBeamTask:
    """Class to track tasks of component manager long running commands.

    This class wraps the logic of having an :py:class::`AggregateRemoteTask`
    to be used within the :py:class::`PstBeamComponentManager` calls such
    as `scan`, `assign`, `release`, etc.

    As this class is callable, it can be used within a background task and
    executed on a separate thread.
    """

    def __init__(
        self: _PstBeamTask,
        action: Callable[[PstDeviceProxy], Any],
        devices: List[PstDeviceProxy],
        task_callback: Callable,
    ):
        """Initialise task.

        :param action: the action to call on each of the device proxies.
        :param devices: a list of :py:class::`PstDeviceProxy` that the
            action will delegate to.
        :param task_callback: a callback used by the base task tracker
            that can be notified of changes in progress and status
            of the task.
        """
        self._devices = devices
        self._action = action
        self._task_callback = task_callback

        self._task = AggregateRemoteTask(task_callback=task_callback)
        for d in devices:
            self._task.add_remote_task(
                device=d,
                action=action,
            )

    def __call__(self: _PstBeamTask, *args: Any, **kwds: Any) -> Any:
        """Execute task."""
        return self._task()


class PstBeamComponentManager(PstComponentManager):
    """Component manager for the BEAM component in PST.LMC.

    Since the BEAM component is a logical device, this component
    manager is used to orchestrate the process devices, such as
    BEAM, RECV.

    Commands that are executed on this component manager are
    sent to instances of :py:class::`PstDeviceProxy` for each
    device that the BEAM device manages.

    This component manager only takes the fully-qualified device
    name (FQDN) for the remote devices, but uses the
    :py:class::`DeviceProxyFactory` to retrieve instances of the
    device proxies that commands should be sent to.
    """

    _smrb_device: PstDeviceProxy
    _recv_device: PstDeviceProxy

    def __init__(
        self: PstBeamComponentManager,
        smrb_fqdn: str,
        recv_fqdn: str,
        simulation_mode: SimulationMode,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        background_task_processor: Optional[BackgroundTaskProcessor] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialise component manager.

        :param smrb_fqdn: the fully qualified device name (FQDN) of the
            shared memory ring buffer (SMRB) TANGO device.
        :param recv_fqdn: the FQDN of the Receive TANGO device.
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        self._smrb_device = DeviceProxyFactory.get_device(smrb_fqdn)
        self._recv_device = DeviceProxyFactory.get_device(recv_fqdn)
        self._remote_devices = [self._smrb_device, self._recv_device]
        self._background_task_processor = background_task_processor or BackgroundTaskProcessor(
            default_logger=logger,
        )
        super().__init__(
            simulation_mode, logger, communication_state_callback, component_state_callback, *args, **kwargs
        )

    def _handle_communication_state_change(
        self: PstBeamComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            # fake going through states to have the communication established.
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._component_state_callback(fault=None, power=PowerState.OFF)
        elif communication_state == CommunicationStatus.DISABLED:
            self._update_communication_state(CommunicationStatus.DISABLED)
            self._component_state_callback(fault=None, power=PowerState.UNKNOWN)

    def update_admin_mode(self: PstBeamComponentManager, admin_mode: AdminMode) -> None:
        """Update the admin mode of the remote devices.

        The adminMode of the remote devices should only be managed through the BEAM
        device, and this method is called from the :py:class::`PstBeam` device to
        make sure that the component manager will update the remote devices.
        """
        self._smrb_device.adminMode = admin_mode
        self._recv_device.adminMode = admin_mode

    def assign(self: PstBeamComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """
        resources_str = json.dumps(resources)
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.AssignResources(resources_str),
            task_callback=task_callback,
        )
        # make sure we hold a reference
        task.resources = resources_str  # type: ignore

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "Resourcing"

    def release(self: PstBeamComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Release resources from the component.

        :param resources: resources to be released
        """
        resources_str = json.dumps(resources)
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.ReleaseResources(resources_str),
            task_callback=task_callback,
        )
        # make sure we hold a reference
        task.resources = resources_str  # type: ignore

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "Releasing"

    def release_all(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Release all resources."""
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.ReleaseAllResources(),
            task_callback=task_callback,
        )

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "Releasing all"

    def configure(
        self: PstBeamComponentManager, configuration: dict, task_callback: Callable
    ) -> TaskResponse:
        """
        Configure the component.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        configuration_str = json.dumps(configuration)
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.Configure(configuration_str),
            task_callback=task_callback,
        )
        # make sure we hold a reference
        task.configuration = configuration_str  # type: ignore

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "Configuring"

    def deconfigure(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure this component."""
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.End(),
            task_callback=task_callback,
        )

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "Deconfiguring"

    def scan(self: PstBeamComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""
        # should be for how long the scan is and update based on that.
        args_str = json.dumps(args)
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.Scan(args_str),
            task_callback=task_callback,
        )
        # make sure we hold a reference
        task.args = args_str  # type: ignore

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "Scanning"

    def end_scan(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """End scanning."""
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.EndScan(),
            task_callback=task_callback,
        )

        self._background_task_processor.submit_task(task)
        return TaskStatus.QUEUED, "End scanning"

    def abort(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""
        task = _PstBeamTask(
            devices=[self._smrb_device, self._recv_device],
            action=lambda d: d.Abort(),
            task_callback=task_callback,
        )

        self._background_task_processor.submit_task(task)
        return TaskStatus.IN_PROGRESS, "Aborting"
