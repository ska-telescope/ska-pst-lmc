# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Test to the RECV Tango device for PST.LMC."""

from __future__ import annotations

import json
import logging
import time

import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DeviceProxy, DevState

from ska_pst_lmc.smrb.smrb_device import PstSmrb

logger = logging.getLogger(__name__)


class TestPstSmrb:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture(scope="class")
    def device_test_config(self: TestPstSmrb, device_properties: dict) -> dict:
        """
        Specify device configuration, including properties and memorized attributes.

        This implementation provides a concrete subclass of
        SKABaseDevice, and a memorized value for adminMode.

        :param device_properties: fixture that returns device properties
            of the device under test

        :return: specification of how the device under test should be
            configured
        """
        return {
            "device": PstSmrb,
            "process": True,
            "properties": device_properties,
            "memorized": {"adminMode": str(AdminMode.ONLINE.value)},
        }

    def test_State(self: TestPstSmrb, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_GetVersionInfo(self: TestPstSmrb, device_under_test: DeviceProxy) -> None:
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

    def test_configure_then_scan_then_stop(self: TestPstSmrb, device_under_test: DeviceProxy) -> None:
        """Test state model of PstSmrb."""
        # need to go through state mode
        assert device_under_test.state() == DevState.OFF

        device_under_test.On()
        time.sleep(0.1)
        assert device_under_test.state() == DevState.ON

        # need to assign resources
        assert device_under_test.obsState == ObsState.EMPTY

        resources = json.dumps({"foo": "bar"})
        device_under_test.AssignResources(resources)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.RESOURCING
        time.sleep(0.3)
        assert device_under_test.obsState == ObsState.IDLE

        configuration = json.dumps({"nchan": 1024})
        device_under_test.Configure(configuration)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.CONFIGURING
        time.sleep(0.3)
        assert device_under_test.obsState == ObsState.READY

        scan = json.dumps({"cat": "dog"})
        device_under_test.Scan(scan)
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.READY
        time.sleep(0.3)
        assert device_under_test.obsState == ObsState.SCANNING

        time.sleep(5)
        # shoud now be able to get some properties
        assert device_under_test.ring_buffer_utilisation > 0.0
        assert device_under_test.ring_buffer_size > 0
        assert device_under_test.number_subbands > 0

        for i in range(device_under_test.number_subbands):
            assert device_under_test.subband_ring_buffer_utilisations[i] > 0.0
            assert device_under_test.subband_ring_buffer_sizes[i] > 0

        device_under_test.EndScan()
        time.sleep(0.1)
        assert device_under_test.obsState == ObsState.SCANNING
        time.sleep(0.3)
        assert device_under_test.obsState == ObsState.READY

        logger.info("Device is now in ready state.")

        device_under_test.Off()
        time.sleep(0.1)
        assert device_under_test.state() == DevState.OFF
