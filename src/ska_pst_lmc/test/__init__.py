# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE.txt for more info.
"""This subpackage with test TANGO device as client."""

__all__ = [
    "TestMockServicer",
    "TestPstLmcService",
]

from .test_grpc_server import TestMockServicer, TestPstLmcService
