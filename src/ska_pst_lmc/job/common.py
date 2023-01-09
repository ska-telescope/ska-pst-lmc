# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for handling long running jobs."""

from __future__ import annotations

from typing import Callable

from ska_tango_base.base.base_device import DevVarLongStringArrayType

from ska_pst_lmc.device_proxy import PstDeviceProxy

DeviceAction = Callable[[PstDeviceProxy], DevVarLongStringArrayType]
"""A type alias representing a callable of a long running command on a device proxy."""
