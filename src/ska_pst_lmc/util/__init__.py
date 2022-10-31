# -*- coding: utf-8 -*-

"""This module covers common utility classes and functions of PST.LMC.

Functionality provided within this module is:

    * Validation of JSON requests
    * Background Task processing
    * Long running command processing
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
    "LongRunningCommandInterface",
    "TimeoutIterator",
    "Callback",
    "CallbackNoArgs",
]

from .configuration import Configuration
from .validation import validate, Strictness
from .background_task import BackgroundTaskProcessor, BackgroundTask, RunState, background_task
from .remote_task import RemoteTask, AggregateRemoteTask
from .long_running_command_interface import LongRunningCommandInterface
from .timeout_iterator import TimeoutIterator
from .callback import Callback, CallbackNoArgs
