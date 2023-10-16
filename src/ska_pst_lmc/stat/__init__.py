# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE.txt for more info.
"""This subpackage implements STAT component for PST.LMC."""

__all__ = [
    "PstStatSimulator",
    "StatMonitorData",
    "StatMonitorDataStore",
    "DEFAULT_NUM_REBIN",
    "DEFAULT_PROCESSING_DELAY_MS",
    "DEFAULT_REQ_FREQ_BINS",
    "DEFAULT_REQ_TIME_BINS",
    "calculate_stat_subband_resources",
    "generate_stat_scan_request",
]

from .stat_model import StatMonitorData, StatMonitorDataStore
from .stat_simulator import PstStatSimulator
from .stat_util import (
    DEFAULT_NUM_REBIN,
    DEFAULT_PROCESSING_DELAY_MS,
    DEFAULT_REQ_FREQ_BINS,
    DEFAULT_REQ_TIME_BINS,
    calculate_stat_subband_resources,
    generate_stat_scan_request,
)
