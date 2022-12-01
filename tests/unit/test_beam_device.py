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
import queue
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import backoff
import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DeviceProxy, DevState
from tango.test_context import MultiDeviceTestContext

from ska_pst_lmc import PstBeam, PstDsp, PstReceive, PstSmrb
from ska_pst_lmc.device_proxy import DeviceProxyFactory
from ska_pst_lmc.dsp.dsp_model import DEFAULT_RECORDING_TIME
from tests.conftest import TangoChangeEventHelper, TangoDeviceCommandChecker


@pytest.fixture
def additional_change_events_callbacks() -> List[str]:
    """Return additional change event callbacks."""
    return [
        "dataReceiveRate",
        "dataReceived",
        "dataDropRate",
        "dataDropped",
        "dataRecordRate",
        "dataRecorded",
        "diskAvailableBytes",
        "availableRecordingTime",
        "ringBufferUtilisation",
    ]


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
                    "properties": {
                        "monitor_polling_rate": 100,
                    },
                }
            ],
        },
        {
            "class": PstReceive,
            "devices": [
                {
                    "name": "test/recv/1",
                    "properties": {
                        "monitor_polling_rate": 100,
                    },
                }
            ],
        },
        {
            "class": PstSmrb,
            "devices": [
                {
                    "name": "test/smrb/1",
                    "properties": {
                        "monitor_polling_rate": 100,
                    },
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


class _AttributeEventValidator:
    """Class to validate attribute events between BEAM and subordinate devices."""

    def __init__(
        self: _AttributeEventValidator,
        device_under_test: DeviceProxy,
        source_device_fqdn: str,
        attribute_name: str,
        default_value: Any,
        tango_change_event_helper: TangoChangeEventHelper,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """Initialise validator."""
        self.device_under_test = device_under_test
        self.source_device = DeviceProxyFactory.get_device(source_device_fqdn)
        self.attribute_name = attribute_name
        self.default_value = default_value

        self.attribute_value_queue: queue.Queue[Any] = queue.Queue()
        self.change_event_callbacks = change_event_callbacks

        tango_change_event_helper.subscribe(attribute_name)
        change_event_callbacks[attribute_name].assert_change_event(default_value)

        self.source_device.subscribe_change_event(attribute_name, self.attribute_value_queue.put)

    def assert_initial_values(self: _AttributeEventValidator) -> None:
        """Assert initial values of BEAM and subordinate device as the same."""

        def _get_values() -> Tuple[Any, Any]:
            return getattr(self.device_under_test, self.attribute_name), getattr(
                self.source_device, self.attribute_name
            )

        initial_values = _get_values()

        if self.attribute_name != "diskAvailableBytes":
            # diskAvailableBytes actually changes from a default value a new value when the On command
            # happens
            assert (
                initial_values[0] == self.default_value
            ), f"{self.attribute_name} on {self.device_under_test} not {self.default_value} but {initial_values[0]}"  # noqa: E501
            assert (
                initial_values[1] == self.default_value
            ), f"{self.attribute_name} on {self.device_under_test} not {self.default_value} but {initial_values[1]}"  # noqa: E501

    def assert_values(self: _AttributeEventValidator) -> None:
        """Assert that the events on BEAM as those from subordinate device."""
        # use None as a sentinal value to break out of assertion loop
        self.attribute_value_queue.put(None)
        for idx, value in enumerate(self.attribute_value_queue.queue):
            if value is None:
                break

            self.change_event_callbacks[self.attribute_name].assert_change_event(value)


@pytest.mark.forked
class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    def test_beam_mgmt_State(self: TestPstBeam, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.1)

        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_beam_mgmt_GetVersionInfo(self: TestPstBeam, device_under_test: DeviceProxy) -> None:
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

    def test_beam_mgmt_configure_then_scan_then_stop(
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

    def test_beam_mgmt_go_to_fault(
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
            lambda: device_under_test.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
        )
        assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Off(),
        )
        assert_state(DevState.OFF)

    @pytest.mark.forked
    def test_beam_mgmt_scan_monitoring_values(
        self: TestPstBeam,
        device_under_test: DeviceProxy,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_change_event_helper: TangoChangeEventHelper,
        tango_device_command_checker: TangoDeviceCommandChecker,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """Test that monitoring values are updated."""
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.2)

        device_propertry_config = {
            "test/recv/1": {
                "dataReceiveRate": 0.0,
                "dataReceived": 0,
                "dataDropRate": 0.0,
                "dataDropped": 0,
            },
            "test/dsp/1": {
                "dataRecordRate": 0.0,
                "dataRecorded": 0,
                "diskAvailableBytes": sys.maxsize,
                "availableRecordingTime": DEFAULT_RECORDING_TIME,
            },
            "test/smrb/1": {
                "ringBufferUtilisation": 0.0,
            },
        }

        attribute_event_validators = [
            _AttributeEventValidator(
                device_under_test=device_under_test,
                source_device_fqdn=fqdn,
                attribute_name=attribute_name,
                default_value=default_value,
                tango_change_event_helper=tango_change_event_helper,
                change_event_callbacks=change_event_callbacks,
            )
            for fqdn, props in device_propertry_config.items()
            for attribute_name, default_value in props.items()
        ]

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.IDLE]
        )

        # assert initial values.
        for v in attribute_event_validators:
            v.assert_initial_values()

        # need to set up scanning
        configuration = json.dumps(csp_configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )

        scan = str(scan_id)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.Scan(scan),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )

        # wait for a monitoring period?
        time.sleep(0.25)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.EndScan(),
            expected_obs_state_events=[
                ObsState.READY,
            ],
        )

        # Assert attribute values
        for v in attribute_event_validators:
            v.assert_values()
