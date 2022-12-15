# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for handling long running jobs."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

from ska_pst_lmc.device_proxy import PstDeviceProxy
from ska_pst_lmc.util.callback import Callback, callback_safely

from .common import DeviceAction


@dataclass(kw_only=True)
class TaskContext:
    """A class used to track a task when a job is running."""

    task: Task
    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    evt: threading.Event = field(default_factory=threading.Event, repr=False)
    parent_task_context: Optional[TaskContext] = None
    result: Optional[Any] = None
    exception: Optional[Exception] = None

    def signal_complete(self: TaskContext, result: Optional[Any] = None) -> None:
        self.result = result
        self.evt.set()

    def signal_failed(self: TaskContext, exception: Exception) -> None:
        self.exception = exception
        self.evt.set()

    def signal_failed_from_str(self: TaskContext, msg: str) -> None:
        try:
            raise RuntimeError(msg)
        except Exception as e:
            self.signal_failed(exception=e)

    @property
    def failed(self: TaskContext) -> bool:
        return self.exception is not None

    @property
    def completed(self: TaskContext) -> bool:
        return self.failed or self.result is not None


@dataclass(kw_only=True)
class ParallelTaskContext(TaskContext):
    """A task context class that tracks subtasks for a parallel task"""

    subtasks: List[TaskContext] = field(default_factory=list)


@dataclass(kw_only=True)
class DeviceCommandTaskContext(TaskContext):
    """A task context class that is used for Tango Device Proxy command tasks."""

    device: PstDeviceProxy
    action: DeviceAction
    command_name: str


@dataclass(kw_only=True)
class JobContext(TaskContext):
    """A task context class that is used to track the whole submitted job."""

    success_callback: Callback = None
    failure_callback: Callback = None

    def signal_complete(self: JobContext, result: Optional[Any] = None) -> None:
        super().signal_complete(result)
        callback_safely(self.success_callback)

    def signal_failed(self: JobContext, exception: Exception) -> None:
        super().signal_failed(exception)
        callback_safely(self.failure_callback, exception=exception)


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
