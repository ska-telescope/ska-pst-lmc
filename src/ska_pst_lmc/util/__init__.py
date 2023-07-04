# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""
This module covers common utility classes and functions of PST.LMC.

Functionality provided within this module is:

    * Validation of JSON requests
    * Background Task processing
    * Job processing, including running jobs in parallel/sequential and on remote Device TANGO devices
    * Custom timeout iterator (see :py:class:`TimeoutIterator`)
"""

__all__ = [
    "validate",
    "Strictness",
    "ValidationError",
    "Configuration",
    "BackgroundTask",
    "BackgroundTaskProcessor",
    "background_task",
    "RunState",
    "RemoteTask",
    "AggregateRemoteTask",
    "TimeoutIterator",
    "Callback",
    "TelescopeFacilityEnum",
]

from .configuration import Configuration
from .validation import validate, Strictness, ValidationError
from .background_task import BackgroundTaskProcessor, BackgroundTask, RunState, background_task
from .remote_task import RemoteTask, AggregateRemoteTask
from .timeout_iterator import TimeoutIterator
from .callback import Callback
from .telescope_facility import TelescopeFacilityEnum
