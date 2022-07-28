# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Test to the RECV Tango device for PST.LMC."""

from __future__ import annotations

import json
import time
from typing import Dict, Generator

import pytest
from ska_tango_base.commands import TaskStatus
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DeviceProxy, DevState
from tango.test_context import DeviceTestContext

from ska_pst_lmc import PstReceive
from ska_pst_lmc.receive import generate_random_update
from ska_pst_lmc.receive.receive_model import ReceiveData
from tests.conftest import TangoChangeEventHelper


@pytest.fixture()
def receive_device() -> Generator[DeviceProxy, None, None]:
    """Create text fixture that yields a DeviceProxy for RECV TANGO device."""
    with DeviceTestContext(PstReceive) as proxy:
        yield proxy


@pytest.fixture()
def receive_data() -> ReceiveData:
    """Generate a receive data object.

    This will generate random data for a ReceiveData that can be used
    in testing to assert that the device updates its attributes in
    a known way.
    """
    return generate_random_update()


class TestPstReceive:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture(scope="class")
    def device_test_config(self: TestPstReceive, device_properties: dict) -> dict:
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
            "device": PstReceive,
            "process": True,
            "properties": device_properties,
            "memorized": {"adminMode": str(AdminMode.ONLINE.value)},
        }

    def test_State(self: TestPstReceive, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_GetVersionInfo(self: TestPstReceive, device_under_test: DeviceProxy) -> None:
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
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        tango_change_event_helper: TangoChangeEventHelper,
    ) -> None:
        """Test state model of PstReceive."""
        long_running_command_result_callback = tango_change_event_helper.subscribe("longRunningCommandResult")
        long_running_command_result_callback.assert_next_change_event(("", ""))

        long_running_command_status_callback = tango_change_event_helper.subscribe("longRunningCommandStatus")

        def assert_command_status(command_id: str, status: str) -> None:
            evt = long_running_command_status_callback.get_next_change_event()

            # need to covert to map
            evt_iter = iter(evt)
            evt_map: Dict[str, str] = {k: v for (k, v) in zip(evt_iter, evt_iter)}

            assert command_id in evt_map
            assert evt_map[command_id] == status

        # need to go through state mode
        assert device_under_test.state() == DevState.OFF

        [[result], [command_id]] = device_under_test.On()
        assert result == TaskStatus.IN_PROGRESS

        # long_running_command_result_callback.assert_next_change_event((command_id, 'QUEUED'))
        assert_command_status(command_id, "QUEUED")
        assert_command_status(command_id, "IN_PROGRESS")
        assert_command_status(command_id, "COMPLETED")
        long_running_command_result_callback.assert_next_change_event((command_id, '"Completed"'))

        assert device_under_test.state() == DevState.ON

        assert device_under_test.obsState == ObsState.EMPTY

        resources = json.dumps({"foo": "bar"})
        [[result], [command_id]] = device_under_test.AssignResources(resources)

        assert result == TaskStatus.IN_PROGRESS

        assert_command_status(command_id, "IN_PROGRESS")
        assert_command_status(command_id, "COMPLETED")
        long_running_command_result_callback.assert_next_change_event((command_id, '"Completed"'))

        assert device_under_test.obsState == ObsState.IDLE

        configuration = json.dumps({"nchan": 1024})
        [[result], [command_id]] = device_under_test.Configure(configuration)
        assert result == TaskStatus.IN_PROGRESS

        assert_command_status(command_id, "IN_PROGRESS")
        assert device_under_test.obsState == ObsState.CONFIGURING

        assert_command_status(command_id, "COMPLETED")
        long_running_command_result_callback.assert_next_change_event((command_id, '"Completed"'))
        assert device_under_test.obsState == ObsState.READY

        scan = json.dumps({"cat": "dog"})
        [[result], [command_id]] = device_under_test.Scan(scan)
        assert result == TaskStatus.IN_PROGRESS

        assert_command_status(command_id, "QUEUED")
        assert_command_status(command_id, "IN_PROGRESS")
        assert_command_status(command_id, "COMPLETED")
        long_running_command_result_callback.assert_next_change_event((command_id, '"Completed"'))
        assert device_under_test.obsState == ObsState.SCANNING

        # shoud now be able to get some properties
        # when we add polling parameter to RECV we can reduce this timeout
        time.sleep(5.5)
        assert device_under_test.received_rate > 0.0
        assert device_under_test.received_data > 0
        assert device_under_test.dropped_rate > 0.0
        assert device_under_test.dropped_data > 0
        assert device_under_test.misordered_packets >= 0
        assert device_under_test.malformed_packets >= 0
        assert device_under_test.relative_weight > 0.0
        assert len(device_under_test.relative_weights) == 1024

        [[result], [command_id]] = device_under_test.EndScan()
        assert result == TaskStatus.IN_PROGRESS

        assert_command_status(command_id, "QUEUED")
        assert_command_status(command_id, "IN_PROGRESS")
        assert device_under_test.obsState == ObsState.SCANNING
        assert_command_status(command_id, "COMPLETED")
        long_running_command_result_callback.assert_next_change_event((command_id, '"Completed"'))
        assert device_under_test.obsState == ObsState.READY

        [[result], [command_id]] = device_under_test.Off()
        assert_command_status(command_id, "QUEUED")
        assert_command_status(command_id, "IN_PROGRESS")
        assert result == TaskStatus.IN_PROGRESS
        assert_command_status(command_id, "COMPLETED")
        long_running_command_result_callback.assert_next_change_event((command_id, '"Completed"'))
        assert device_under_test.state() == DevState.OFF
