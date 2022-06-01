# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains pytests for integration tests."""

from __future__ import annotations

import json
import time

import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DevState

from ska_pst_lmc import DeviceProxyFactory

pytestmark = pytest.mark.integration


class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    def test_configure_then_scan_then_stop(self: TestPstBeam) -> None:
        """Test state model of PstReceive."""
        # need to go through state mode

        recv_proxy = DeviceProxyFactory.get_device("test/receive/1")
        smrb_proxy = DeviceProxyFactory.get_device("test/smrb/1")
        beam_proxy = DeviceProxyFactory.get_device("test/beam/1")

        def assert_state(state: DevState) -> None:
            assert beam_proxy.state() == state
            assert recv_proxy.state() == state
            assert smrb_proxy.state() == state

        def assert_obstate(obsState: ObsState) -> None:
            assert beam_proxy.obsState == obsState
            assert recv_proxy.obsState == obsState
            assert smrb_proxy.obsState == obsState

        # better handle of setup and teardown
        assert_state(DevState.DISABLE)

        beam_proxy.adminMode = AdminMode.ONLINE
        time.sleep(0.1)
        assert recv_proxy.adminMode == AdminMode.ONLINE
        assert smrb_proxy.adminMode == AdminMode.ONLINE

        assert_state(DevState.OFF)

        try:
            beam_proxy.On()
            time.sleep(0.2)
            assert_state(DevState.ON)

            # need to assign resources
            assert_obstate(ObsState.EMPTY)

            resources = json.dumps({"foo": "bar"})
            beam_proxy.AssignResources(resources)
            time.sleep(0.1)

            assert_obstate(ObsState.RESOURCING)

            time.sleep(1)

            assert_obstate(ObsState.IDLE)

            configuration = json.dumps({"nchan": 1024})
            beam_proxy.Configure(configuration)

            time.sleep(0.1)
            assert_obstate(ObsState.CONFIGURING)

            time.sleep(0.3)
            assert_obstate(ObsState.READY)

            scan = json.dumps({"cat": "dog"})
            beam_proxy.Scan(scan)
            time.sleep(0.1)

            assert_obstate(ObsState.READY)
            time.sleep(0.3)
            assert_obstate(ObsState.SCANNING)

            beam_proxy.EndScan()
            time.sleep(0.1)
            assert_obstate(ObsState.SCANNING)
            time.sleep(0.5)
            assert_obstate(ObsState.READY)

            beam_proxy.Off()
            time.sleep(0.5)

            assert_state(DevState.OFF)
        finally:
            beam_proxy.Off()
            time.sleep(0.5)
            beam_proxy.adminMode = AdminMode.OFFLINE
            time.sleep(0.1)
            assert recv_proxy.adminMode == AdminMode.OFFLINE
            assert smrb_proxy.adminMode == AdminMode.OFFLINE

            assert_state(DevState.DISABLE)
