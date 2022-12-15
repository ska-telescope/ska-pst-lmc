# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for handling long running jobs."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import List, Union

from ska_pst_lmc.device_proxy import PstDeviceProxy
from ska_pst_lmc.util.callback import Callback

from .common import DeviceAction


@dataclass
class SequentialJob:
    """A class used to handle sequential jobs.

    Instances of this class take a list of jobs that will all
    be run in sequentially. This job is not complete until the
    last job is complete.

    :param tasks: a list of subtasks/jobs to be performed sequentially
    :type tasks: List[Job]
    """

    tasks: List[Job]


@dataclass
class ParallelJob:
    """A class used to handle jobs that can be run in parallel.

    Instances of this class take a list of jobs that can be all
    run in parallel. This job is not complete until all the jobs
    are complete.

    :param tasks: a list of subtasks/jobs to be performed concurrently
    :type tasks: List[Job]
    """

    tasks: List[Job]


@dataclass
class DeviceCommandJob:
    """A class used to handle a command to be executed on remote devices.

    Instances of this class take a list of devices and an action to
    be performed on a remote device. If more than one device is used this
    is converted into a :py:class:`ParallelJob` that separate instances
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


Job = Union[SequentialJob, ParallelJob, DeviceCommandJob]
"""Type alias for the different sorts of jobs."""


@dataclass
class JobContext:
    """A data class representing a job and the callback to use when complete.

    :param job: the job the needs to be executed.
    :param callback: the optional callback to use when job is complete, default is None.
    """

    job: Job
    callback: Callback = None

    def __repr__(self: JobContext) -> str:
        """Create a string representation of JobContext.

        :return: a string representation of a JobContext
        :rtype: str
        """
        return f"JobContext(job='{self.job}')"


@dataclass
class ParallelJobContext:
    """A data class representiong the job context for a `ParallelJob`.

    :param job_id: a UUID string representing the job.
    :param task_signals: a list of :py:class:`threading.Event` used to track the state of
        the subtasks. There is one signal per subtask.
    :param signal: the signal used to notify the whole job is complete, which in turn can
        then call the job's associated callback.
    """

    job_id: str
    tasks_signals: List[threading.Event] = field(repr=False)
    signal: threading.Event = field(repr=False)


@dataclass
class ParallelJobTaskContext:
    """A data class representing the job context of a subtask for a `ParallelJob`.

    :param job_id: a UUID string representing the job.
    :param task_id: a UUID string representing the subtask.
    :param job: the job the subtask is to perform, this maybe a `SequentialJob`, a
        `DeviceCommandJob` or even another `ParallelJob`.
    :param signal: the signal used to notify the subtask is complete. This signal is
        also stored in the `task_signals` field of a `ParallelJobContext`.
    """

    job_id: str
    task_id: str
    job: Job
    signal: threading.Event = field(repr=False)


@dataclass
class DeviceCommandJobContext:
    """A data class representing the job context of a `DeviceCommandJob`.

    :param device: the device that the action is to be performed against.
    :param action: the action to perform on the device proxy.
    :param signal: the signal used to notify the command is complete. Since
        device commands run in the background on a remote device, this signal
        is used to notify the executor that this remote job is complete.
    """

    device: PstDeviceProxy
    command_name: str
    action: DeviceAction = field(repr=False)
    signal: threading.Event = field(repr=False)
