# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Test to the BEAM Tango device for PST.LMC."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

import backoff
import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DeviceProxy, DevState
from tango.test_context import MultiDeviceTestContext

from ska_pst_lmc import PstBeam, PstDsp, PstReceive, PstSmrb
from tests.conftest import TangoDeviceCommandChecker


@pytest.fixture()
def device_under_test(multidevice_test_context: MultiDeviceTestContext) -> DeviceProxy:
    """Create text fixture that yields a DeviceProxy for BEAM TANGO device."""
    time.sleep(0.15)
    return multidevice_test_context.get_device("test/beam/1")


@pytest.fixture(scope="class")
def server_configuration(devices_info: List[dict]) -> dict:
    """Get BEAM server configuration for tests."""
    return {
        "devices_info": devices_info,
        "process": True,
        "server_name": "TestBeamServer",
        "instance_name": "test_beam_server_0",
        "debug": 4,
        "host": "127.0.0.1",
    }


@pytest.fixture(scope="class")
def devices_info() -> List[dict]:
    """Get device configuration for tests."""
    return [
        {
            "class": PstDsp,
            "devices": [
                {
                    "name": "test/dsp/1",
                    "properties": {},
                }
            ],
        },
        {
            "class": PstReceive,
            "devices": [
                {
                    "name": "test/recv/1",
                    "properties": {},
                }
            ],
        },
        {
            "class": PstSmrb,
            "devices": [
                {
                    "name": "test/smrb/1",
                    "properties": {},
                }
            ],
        },
        {
            "class": PstBeam,
            "devices": [
                {
                    "name": "test/beam/1",
                    "properties": {
                        "beam_id": "1",
                        "RecvFQDN": "test/recv/1",
                        "SmrbFQDN": "test/smrb/1",
                        "DspFQDN": "test/dsp/1",
                        "SendFQDN": "test/send/1",
                    },
                }
            ],
        },
    ]


class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    def test_State(self: TestPstBeam, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.1)

        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_GetVersionInfo(self: TestPstBeam, device_under_test: DeviceProxy) -> None:
        """
        Test for GetVersionInfo.

        :param device_under_test: a proxy to the device under test
        """
        import re

        version_pattern = (
            f"{device_under_test.info().dev_class}, ska_pst_lmc, "
            "[0-9]+.[0-9]+.[0-9]+, A set of PST LMC tango devices for the SKA Low and Mid Telescopes."
        )
        version_info = device_under_test.GetVersionInfo()
        assert len(version_info) == 1
        assert re.match(version_pattern, version_info[0])

    @pytest.mark.forked
    def test_configure_then_scan_then_stop(
        self: TestPstBeam,
        device_under_test: DeviceProxy,
        multidevice_test_context: MultiDeviceTestContext,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_device_command_checker: TangoDeviceCommandChecker,
        logger: logging.Logger,
    ) -> None:
        """Test state model of PstReceive."""
        # need to go through state mode
        dsp_proxy = multidevice_test_context.get_device("test/recv/1")
        recv_proxy = multidevice_test_context.get_device("test/recv/1")
        smrb_proxy = multidevice_test_context.get_device("test/smrb/1")
        # trying to avoid potential race condition inside TANGO
        time.sleep(0.1)

        def assert_state(state: DevState) -> None:
            assert device_under_test.state() == state
            assert recv_proxy.state() == state
            assert smrb_proxy.state() == state
            assert dsp_proxy.state() == state

        @backoff.on_exception(
            backoff.expo,
            AssertionError,
            factor=1,
            max_time=5.0,
        )
        def assert_obstate(obsState: ObsState, subObsState: Optional[ObsState] = None) -> None:
            assert device_under_test.obsState == obsState

            if subObsState is not None:
                assert recv_proxy.obsState == subObsState
                assert smrb_proxy.obsState == subObsState
                assert dsp_proxy.obsState == subObsState
            else:
                assert recv_proxy.obsState == obsState
                assert smrb_proxy.obsState == obsState
                assert dsp_proxy.obsState == obsState

        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.1)
        assert recv_proxy.adminMode == AdminMode.ONLINE
        assert smrb_proxy.adminMode == AdminMode.ONLINE
        assert dsp_proxy.adminMode == AdminMode.ONLINE

        assert_state(DevState.OFF)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.IDLE]
        )
        assert_state(DevState.ON)

        assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

        configuration = json.dumps(csp_configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )
        assert_obstate(ObsState.READY)

        scan = str(scan_id)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.Scan(scan),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )
        assert_obstate(ObsState.SCANNING)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.EndScan(),
            expected_obs_state_events=[
                ObsState.READY,
            ],
        )
        assert_obstate(ObsState.READY)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToIdle(),
            expected_obs_state_events=[
                ObsState.IDLE,
            ],
        )
        assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Off(),
        )
        assert_state(DevState.OFF)

    @pytest.mark.forked
    def test_go_to_fault(
        self: TestPstBeam,
        device_under_test: DeviceProxy,
        multidevice_test_context: MultiDeviceTestContext,
        tango_device_command_checker: TangoDeviceCommandChecker,
        logger: logging.Logger,
    ) -> None:
        """Test state model of PstReceive."""
        # need to go through state mode
        dsp_proxy = multidevice_test_context.get_device("test/dsp/1")
        recv_proxy = multidevice_test_context.get_device("test/recv/1")
        smrb_proxy = multidevice_test_context.get_device("test/smrb/1")
        # trying to avoid potential race condition inside TANGO
        time.sleep(0.1)

        def assert_state(state: DevState) -> None:
            assert device_under_test.state() == state
            assert recv_proxy.state() == state
            assert smrb_proxy.state() == state
            assert dsp_proxy.state() == state

        @backoff.on_exception(
            backoff.expo,
            AssertionError,
            factor=1,
            max_time=5.0,
        )
        def assert_obstate(obsState: ObsState, subObsState: Optional[ObsState] = None) -> None:
            assert device_under_test.obsState == obsState
            assert recv_proxy.obsState == subObsState or obsState
            assert smrb_proxy.obsState == subObsState or obsState
            assert dsp_proxy.obsState == subObsState or obsState

        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.1)
        assert recv_proxy.adminMode == AdminMode.ONLINE
        assert smrb_proxy.adminMode == AdminMode.ONLINE
        assert dsp_proxy.adminMode == AdminMode.ONLINE

        assert_state(DevState.OFF)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.IDLE]
        )
        assert_state(DevState.ON)

        # need to configure beam
        assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToFault(),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert_obstate(ObsState.FAULT)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Off(),
        )
        assert_state(DevState.OFF)
