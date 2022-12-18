# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for handling tasks and the task context for background jobs.

This module provides for 3 types of tasks: :py:class:`SequentialTask`,
:py:class:`ParallelTask`, and :py:class:`DeviceCommandTask`. A job
that can be submitted to for background processing can be any of these
types of tasks.  The `SequentialTask` and `ParallelTask` task classes
are composite task classes that have subtasks that can be of any type
of task.

This module also provides a heirarchy of :py:class:`TaskContext` classes.
These are used within the task executors to keep track for the tasks,
and their subtasks. A task context may have an optional parent task context
is used to send information back to the parent and ultimately back up to
job the that was submitted.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

from ska_pst_lmc.device_proxy import PstDeviceProxy
from ska_pst_lmc.util.callback import Callback

from .common import DeviceAction


@dataclass
class SequentialTask:
    """A class used to handle sequential tasks.

    Instances of this class take a list of tasks that will all
    be run in sequentially. This job is not complete until the
    last job is complete.

    :param tasks: a list of subtasks to be performed sequentially
    :type tasks: List[Task]
    """

    subtasks: List[Task]


@dataclass
class ParallelTask:
    """A class used to handle tasks that can be run in parallel.

    Instances of this class take a list of tasks that can be all
    run in parallel. This job is not complete until all the task
    are complete.

    :param tasks: a list of subtasks to be performed concurrently
    :type tasks: List[Task]
    """

    subtasks: List[Task]


@dataclass
class DeviceCommandTask:
    """A class used to handle a command to be executed on remote devices.

    Instances of this class take a list of devices and an action to
    be performed on a remote device. If more than one device is used this
    is converted into a :py:class:`ParallelTask` that separate instances
    of this class, one per device.  This job is not complete until all
    the remote devices have completed the action.

    Commands are sent to the DeviceCommandExecutor to allow to be tracked
    by listening to events on the `longRunningCommandResult` property.

    :param devices: list of devices to perform action upon.
    :type devices: List[PstDeviceProxy]
    :param action: the callbable to perform on each device proxy.
    :type action: Callable[[PstDeviceProxy], DevVarLongStringArrayType]
    """

    devices: List[PstDeviceProxy]
    action: DeviceAction = field(repr=False)
    command_name: str


Task = Union[SequentialTask, ParallelTask, DeviceCommandTask]
"""Type alias for the different sorts of tasks."""


@dataclass(kw_only=True)
class TaskContext:
    """A class used to track a task when a job is running.

    This is the base class for all other types of `TaskContext`. This
    class it used by the job/task executors to keep track of a task
    and is linked back to a parent task. It stores the result or exception
    if the task has completed successfully or failed respectively.

    :ivar task: the task this context relates to.
    :vartype task: Task
    :ivar task_id: the id of the task. If not specified it is a string version
        of a UUID version 4.
    :vartype task_id: str
    :ivar evt: at :py:class:`threading.Event` used to signal that this task
        has finished, either successfully or it failed.
    :vartype evt: threading.Event
    :ivar parent_task_context: an optional parent task context, default None.
    :vartype parent_task_context: Optional[TaskContext]
    :ivar result: the result of the task. Until this value is set the task
        is not considered completed successly.
    :vartype result: Optional[Any]
    :ivar exception: the exception of a failed task. Once this value is set
        the task is considered to have failed.
    """

    task: Task
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evt: threading.Event = field(default_factory=threading.Event, repr=False)
    parent_task_context: Optional[TaskContext] = None
    result: Optional[Any] = None
    exception: Optional[Exception] = None

    def signal_complete(self: TaskContext, result: Optional[Any] = None) -> None:
        """Signal that the task has completed successfully.

        Calling this will mark the task as completed and if any parent task is
        waiting on the `evt` to be set will be notified.

        :param result: the result of the task, if any. This defaults to None
        :type result: Optional[Any], optional
        """
        self.result = result
        self.evt.set()

    def signal_failed(self: TaskContext, exception: Exception) -> None:
        """Signal that the task has failed.

        Calling this will mark the task as failed and if any parent task is
        waiting on the `evt` to be set will be notified.

        :param exception: an exception that will be sent back to the original
            caller of the job that signifies that the command failed.
        :type exception: Exception
        """
        self.exception = exception
        self.evt.set()

    def signal_failed_from_str(self: TaskContext, msg: str) -> None:
        """Signal that the task has failed.

        This takes an error message an raises a `RuntimeError` and then
        calls the `signal_failed` method. This is used by remote device proxies
        where the result returned is the error message of the remote exception.

        :param msg: the error message to convert into a `RuntimeError`
        :type msg: str
        """
        try:
            raise RuntimeError(msg)
        except Exception as e:
            self.signal_failed(exception=e)

    @property
    def failed(self: TaskContext) -> bool:
        """Check if task has failed or not.

        :return: returns True if the context is storing an exception.
        :rtype: bool
        """
        return self.exception is not None

    @property
    def completed(self: TaskContext) -> bool:
        """Check if the task has completed.

        If the task context has failed or there is a result then this
        method will return true.

        :return: if the task has completed
        :rtype: bool
        """
        return self.failed or self.result is not None


@dataclass(kw_only=True)
class ParallelTaskContext(TaskContext):
    """A task context class that tracks subtasks for a parallel task.

    This extends from :py:class:`TaskContext` to allow storing of
    task contexts of the subtasks.

    This task is only considered completedly successfully once on the
    subtasks have completed successfully.  If one of the subtasks fails
    then this task contexted is to be considered failed.

    :ivar subtasks: a list of `TaskContext`, one for each subtask.
    :vartype subtasks: List[TaskContext]
    """

    subtasks: List[TaskContext] = field(default_factory=list)


@dataclass(kw_only=True)
class DeviceCommandTaskContext(TaskContext):
    """A task context class that is used for Tango Device Proxy command tasks.

    This extends from :py:class:`TaskContext` to allow storing of
    task contexts of remote device proxy command tasks.

    :ivar device: the device proxy the command will be executed on.
    :vartype device: PstDeviceProxy
    :ivar action: the action to perform when the task is executed.
    :vartype device: DeviceAction
    :ivar command_name: the name of the command.  This is use for logging/debugging.
    :vartype command_name: str
    """

    device: PstDeviceProxy
    command_name: str
    action: DeviceAction = field(repr=False)


@dataclass(kw_only=True)
class JobContext(TaskContext):
    """A task context class that is used to track the whole submitted job.

    This is used by the job executor to track the overral job. The task
    executor will either throw the exception stored in parent class or
    will call the `success_callback` once the job has been marked as complete.

    :ivar success_callback: an option callback to call when job ends successfully,
        defaults to None.
    :vartype success_callback: Callback
    """

    success_callback: Callback = field(default=None, repr=False)
