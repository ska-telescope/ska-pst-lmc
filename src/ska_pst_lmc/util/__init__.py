# -*- coding: utf-8 -*-

"""This module covers common utility classes and functions of PST.LMC.

Functionality provided within this module is:

    * Validation of JSON requests
    * Background Task processing
    * Job processing, including running jobs in parallel/sequential and on remote Device TANGO devices
    * Custom timeout iterator (see :py:class:`TimeoutIterator`)
"""

__all__ = [
    "validate",
    "Strictness",
    "Configuration",
    "BackgroundTask",
    "BackgroundTaskProcessor",
    "background_task",
    "RunState",
    "RemoteTask",
    "AggregateRemoteTask",
    "TimeoutIterator",
    "Callback",
    "DeviceAction",
    "DeviceCommandJob",
    "DeviceCommandJobExecutor",
    "DeviceCommandJobContext",
    "Job",
    "JobContext",
    "JobExecutor",
    "SequentialJob",
    "ParallelJob",
    "ParallelJobContext",
    "ParallelJobTaskContext",
    "JOB_QUEUE",
    "DEVICE_COMMAND_JOB_QUEUE",
    "JOB_EXECUTOR",
    "DEVICE_COMMAND_JOB_EXECUTOR",
    "submit_job",
]

from .configuration import Configuration
from .validation import validate, Strictness
from .background_task import BackgroundTaskProcessor, BackgroundTask, RunState, background_task
from .remote_task import RemoteTask, AggregateRemoteTask
from .timeout_iterator import TimeoutIterator
from .callback import Callback
from .job import (
    DeviceAction,
    DeviceCommandJob,
    DeviceCommandJobExecutor,
    DeviceCommandJobContext,
    Job,
    JobContext,
    JobExecutor,
    SequentialJob,
    ParallelJob,
    ParallelJobContext,
    ParallelJobTaskContext,
    JOB_QUEUE,
    DEVICE_COMMAND_JOB_QUEUE,
    JOB_EXECUTOR,
    DEVICE_COMMAND_JOB_EXECUTOR,
    submit_job,
)
