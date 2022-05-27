# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module handles tasks that need to be called on device proxies.

Since commands on device proxies may be slow, long running commands, this
module provies classes that can submit and track remote tasks.

The :py:class::`RemoteTask` class deals with calling the task on a remote
device. It subscribes to events of the `longRunningCommandStatus` and
`longRunningCommandProgress` attributes and will proxy the values
of `progress` and `status` back to a task callback method.

The :py:class:`AggregateRemoteTask` class is used when the task has to be
performed on multiple remote devices. It aggregates the progress and the
status. When submitted it will also make sure that the task is run
to completion by checking if all task end, successfully or not.
"""

from __future__ import annotations

import logging
import time
from multiprocessing import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.device_proxy import PstDeviceProxy
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor

TaskResponse = Tuple[TaskStatus, str]
RemoteTaskResponse = Tuple[ResultCode, str]
RemoteAction = Callable[[PstDeviceProxy], RemoteTaskResponse]

__all__ = [
    "RemoteTask",
    "AggregateRemoteTask",
]


class RemoteTask:
    """Class to handle calling long run tasks on remote devices.

    This class takes instances of a device proxy and function/action
    to call when this task is called. It also takes a task_callback
    to be used when the process updates.

    This task will subscribe to events on the device proxy of
    the `longRunningCommandStatus` and `longRunningCommandProgress`
    attributes. When the task is deleted it will unsubscribe from
    the events too.

    This task has to be called (i.e. `task()`) for the action to
    be called. This allows for the task to be submitted as a background
    process/thread.
    """

    command_id: Optional[str] = None
    status: TaskStatus = TaskStatus.STAGING
    progress: Optional[int] = None

    def __init__(
        self: RemoteTask,
        device: PstDeviceProxy,
        action: RemoteAction,
        task_callback: Callable,
    ):
        """Initialise the task.

        :param device: the device proxy that the task is for.
        :param action: the action to perfom when called.
        :param task_callback: the callback to use when the task needs
            to update it's progress or status.
        """
        # should only be able to subscribe to the long running stuff once.
        self.device = device
        self.action = action
        self.task_callback = task_callback

        self._status_subscription = self.device.subscribe_change_event(
            "longRunningCommandStatus",
            self._status_callback,
        )
        self._progress_subscription = self.device.subscribe_change_event(
            "longRunningCommandProgress",
            self._progress_callback,
        )

    def __del__(self: RemoteTask) -> None:
        """Cleam up remote task.

        This makes sure it unsubscribes from events on the attributes
        of the remote device.
        """
        self._status_subscription.unsubscribe()
        self._progress_subscription.unsubscribe()

    def __call__(self: RemoteTask, *arg: Any, **kwargs: Any) -> TaskResponse:
        """Execute the task.

        This executes the action on the remote device.
        """
        (result_code, details) = self.action(self.device)
        # OK = 0            => COMPLETED
        # STARTED = 1       => QUEUED
        # QUEUED = 2        => QUEUED
        # FAILED = 3        => FAILED
        # UNKNOWN = 4       => FAILED
        # REJECTED = 5      => REJECTED
        # NOT_ALLOWED = 6   => FAILED
        # ABORTED = 7       => ABORTED

        if result_code == ResultCode.OK:
            # this only happens if it's not a slow command
            self.status = TaskStatus.COMPLETED
            self.progress = 100
        elif result_code == ResultCode.QUEUED:
            self.status = TaskStatus.QUEUED
            self.command_id = details
            self.progress = 0
        elif result_code == ResultCode.REJECTED:
            self.status = TaskStatus.REJECTED

        return self.status, details

    def _progress_callback(self: RemoteTask, progress_values: List[str]) -> None:
        """Handle change to progress value of long running command.

        When the `longRunningCommandProgress` attribute value changes for the
        remote command, this method is called. It tries to find the value
        for the current process id, if found it will call the task_callback
        if the value has changed from its current value.
        """
        value_iter = iter(progress_values)
        progress_values_map: Dict[str, int] = {k: int(v) for (k, v) in zip(value_iter, value_iter)}

        if self.command_id in progress_values_map:
            progress = progress_values_map[self.command_id]
            if progress != self.progress:
                self.progress = progress
                self.task_callback(progress=progress)

    def _status_callback(self: RemoteTask, status_values: List[str]) -> None:
        """Handle change to status value of long running command.

        When the `longRunningCommandStatus` attribute value changes for the
        remote command, this method is called. It tries to find the value
        for the current process id, if found it will call the task_callback
        if the value has changed from its current value.
        """
        value_iter = iter(status_values)
        status_values_map: Dict[str, TaskStatus] = {
            k: TaskStatus[v] for (k, v) in zip(value_iter, value_iter)
        }

        if self.command_id in status_values_map:
            status = status_values_map[self.command_id]
            if status != self.status:
                self.status = status
                self.task_callback(status=status)


class AggregateRemoteTask:
    """Class for aggregation of multiple remote tasks.

    This class is used to submit multiple remotes tasks that can occur in
    parallel.

    Tasks are added to this aggregate by:

    .. code-block:: python

        task.add_remote_task(
            device,
            action=lambda d: d.Action(),
        )

    Only after all the tasks have been added should this task be submitted.

    This task will also work out the progress and overall status of the task.
    In the case of progress it an average of the progress of all the subtasks
    but there is no weighting of those progress values.
    """

    tasks: List[RemoteTask]
    status: TaskStatus

    def __init__(
        self: AggregateRemoteTask,
        task_callback: Callable,
        background: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialise aggregate task.

        :param task_callback: the callback to use when the task needs
            to update it's progress or status.
        :param background: whether to submit the task in the background or not.
            The default value is True.
        :param logger: the logger to use for logging from this task.
        """
        self.tasks = list()
        self.status = TaskStatus.STAGING
        self.task_callback = task_callback
        self._lock = Lock()
        self._running = False
        self._completed = False
        self._background = background
        self._logger = logger or logging.getLogger(__name__)
        if background:
            self._background_task_processor = BackgroundTaskProcessor(default_logger=self._logger)

    def __call__(self: AggregateRemoteTask) -> TaskResponse:
        """Execute task."""
        if self._background:
            self._background_task_processor.submit_task(action_fn=self._execute_task)
        else:
            self._execute_task()

        return TaskStatus.QUEUED, "Queued"

    def add_remote_task(
        self: AggregateRemoteTask, device: PstDeviceProxy, action: RemoteAction
    ) -> RemoteTask:
        """Add a remote task to be executed when this task executes.

        This can only be called while the task hasn't been already started.

        :param device: the device proxy that the new remote task relates to.
        :param action: the action to perfom on the remote device.
        """
        if self._running:
            raise ValueError("Can't add remote task once called.")

        task = RemoteTask(device=device, action=action, task_callback=self._remote_task_updated)
        self.tasks.append(task)
        return task

    def _execute_task(self: AggregateRemoteTask) -> None:
        """Execute the task.

        This will submit all the remote tasks to run in parallel, i.e. that we don't need
        the first task to complete before even calling the 2nd. However, calling this method
        will make sure that this task runs to completion.
        """
        with self._lock:
            # want to lock so we don't have updates before all the commands are submitted
            self._running = True
            self.status = TaskStatus.IN_PROGRESS
            self.task_callback(status=TaskStatus.IN_PROGRESS, progress=0)
            for t in self.tasks:
                (status_code, details) = t()
                if status_code == TaskStatus.REJECTED:
                    self._logger.warning(f"Remote task for {t.device.fqdn} was rejected. Msg: {details}")
                    self.task_callback(status=TaskStatus.REJECTED)
                    return

        self._run_to_completion()

    def _run_to_completion(self: AggregateRemoteTask, timeout: float = 120.0, sleep: float = 0.1) -> None:
        """Run current task to completion.

        This method will poll to see the current state is in a completed state.
        If the state is in a completed state it will exit, else this will sleep
        for the `sleep` argument value before checking and will timeout after
        the `timeout` value.

        :param timeout: the amount of time to wait before exiting if not complete.
            Default is 120 seconds.
        :param sleep: the amount to sleep between each check. Default is 0.1 second.
        """
        elapsed = 0.0
        while elapsed < timeout:
            with self._lock:
                if self.status not in [TaskStatus.STAGING, TaskStatus.QUEUED, TaskStatus.IN_PROGRESS]:
                    self._completed = True
                    return

            time.sleep(sleep)
            elapsed += sleep

    def _remote_task_updated(self: AggregateRemoteTask, **kwargs: Any) -> None:
        """Handle remote task has been updated.

        This is called when any of the tasks call it's task_progress but
        it will check all the progress and status values of all tasks to
        determine the current progress and status, these values are then
        passed to the `task_callback` that was passed in during the
        construction of this task.
        """
        # happy path
        with self._lock:
            assert len(self.tasks) > 0

            progress = 0
            status = TaskStatus.COMPLETED

            for t in self.tasks:
                progress += t.progress or 0
                if status == TaskStatus.COMPLETED and t.status != TaskStatus.COMPLETED:
                    status = t.status
                elif t.status == TaskStatus.IN_PROGRESS:
                    status = t.status

            if status == TaskStatus.COMPLETED:
                progress = 100
            else:
                progress = int(progress / len(self.tasks))

            self.status = status

            self.task_callback(
                progress=progress,
                status=status,
            )
