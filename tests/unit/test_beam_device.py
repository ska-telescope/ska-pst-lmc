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
from typing import Any, List

import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DeviceProxy, DevState
from tango.test_context import MultiDeviceTestContext

from ska_pst_lmc import PstBeam, PstReceive, PstSmrb

logger = logging.getLogger(__name__)


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

    # @pytest.fixture(scope="class")
    # def device_test_config(self: TestPstBeam, device_properties: dict) -> dict:
    #     """
    #     Specify device configuration, including properties and memorized attributes.

    #     This implementation provides a concrete subclass of
    #     SKABaseDevice, and a memorized value for adminMode.

    #     :param device_properties: fixture that returns device properties
    #         of the device under test

    #     :return: specification of how the device under test should be
    #         configured
    #     """
    #     return {
    #         "device": PstBeam,
    #         "process": True,
    #         "properties": device_properties,
    #         "memorized": {"adminMode": str(AdminMode.OFFLINE.value)},
    #     }

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

    def test_configure_then_scan_then_stop(
        self: TestPstBeam, device_under_test: DeviceProxy, multidevice_test_context: MultiDeviceTestContext
    ) -> None:
        """Test state model of PstReceive."""
        # need to go through state mode

        recv_proxy = multidevice_test_context.get_device("test/recv/1")
        smrb_proxy = multidevice_test_context.get_device("test/smrb/1")

        def assert_state(state: DevState) -> None:
            assert device_under_test.state() == state
            assert recv_proxy.state() == state
            assert smrb_proxy.state() == state

        def assert_obstate(obsState: ObsState) -> None:
            assert device_under_test.obsState == obsState
            assert recv_proxy.obsState == obsState
            assert smrb_proxy.obsState == obsState

        def _event_callback(ev: Any) -> None:
            logger.warning(f"Recevied event: {ev}")

        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.1)
        assert recv_proxy.adminMode == AdminMode.ONLINE
        assert smrb_proxy.adminMode == AdminMode.ONLINE

        assert_state(DevState.OFF)

        device_under_test.On()
        time.sleep(0.5)
        assert_state(DevState.ON)

        # need to assign resources
        assert_obstate(ObsState.EMPTY)

        resources = json.dumps({"foo": "bar"})
        device_under_test.AssignResources(resources)
        time.sleep(0.1)

        assert_obstate(ObsState.RESOURCING)

        time.sleep(1)

        assert_obstate(ObsState.IDLE)

        configuration = json.dumps({"nchan": 1024})
        device_under_test.Configure(configuration)

        time.sleep(0.1)
        assert_obstate(ObsState.CONFIGURING)

        time.sleep(0.5)
        assert_obstate(ObsState.READY)

        scan = json.dumps({"cat": "dog"})
        device_under_test.Scan(scan)
        time.sleep(0.1)

        assert_obstate(ObsState.READY)
        time.sleep(0.5)
        assert_obstate(ObsState.SCANNING)

        device_under_test.EndScan()
        time.sleep(0.1)
        assert_obstate(ObsState.SCANNING)
        time.sleep(0.5)
        assert_obstate(ObsState.READY)

        logger.info("Device is now in ready state.")

        device_under_test.Off()
        time.sleep(0.5)

        assert_state(DevState.OFF)
