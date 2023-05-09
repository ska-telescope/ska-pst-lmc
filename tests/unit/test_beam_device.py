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
from typing import Any, Callable, Dict, List, Optional

import backoff
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, HealthState, ObsState
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DeviceProxy, DevState
from tango.test_context import MultiDeviceTestContext

from ska_pst_lmc import PstBeam, PstDsp, PstReceive, PstSmrb
from tests.conftest import TangoChangeEventHelper, TangoDeviceCommandChecker, _AttributeEventValidator


@pytest.fixture
def additional_change_events_callbacks(beam_attribute_names: List[str]) -> List[str]:
    """Return additional change event callbacks."""
    return [*beam_attribute_names]


@pytest.fixture()
def device_under_test(multidevice_test_context: MultiDeviceTestContext) -> DeviceProxy:
    """Create text fixture that yields a DeviceProxy for BEAM TANGO device."""
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
                        "initial_monitoring_polling_rate": 100,
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
                        "initial_monitoring_polling_rate": 100,
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
                        "initial_monitoring_polling_rate": 100,
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


@pytest.mark.forked
class TestPstBeam:
    """Test class used for testing the PstBeam TANGO device."""

    @pytest.fixture(autouse=True)
    def setup_test_class(
        self: TestPstBeam,
        device_under_test: DeviceProxy,
        multidevice_test_context: MultiDeviceTestContext,
        change_event_callbacks: MockTangoEventCallbackGroup,
        beam_attribute_names: List[str],
        logger: logging.Logger,
    ) -> None:
        """Put test class with Tango devices and event checker."""
        self.beam_proxy = device_under_test
        self.dsp_proxy = multidevice_test_context.get_device("test/recv/1")
        self.recv_proxy = multidevice_test_context.get_device("test/recv/1")
        self.smrb_proxy = multidevice_test_context.get_device("test/smrb/1")
        self._beam_attribute_names = [*beam_attribute_names]

        self.tango_change_event_helper = TangoChangeEventHelper(
            device_under_test=self.beam_proxy,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

        self.tango_device_command_checker = TangoDeviceCommandChecker(
            tango_change_event_helper=self.tango_change_event_helper,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

    def current_attribute_values(self: TestPstBeam) -> Dict[str, Any]:
        """Get current attributate values for BEAM device."""
        # ignore availableDiskSpace as this can change but other props
        # will should get reset when going to Off
        return {
            attr: getattr(self.beam_proxy, attr)
            for attr in self._beam_attribute_names
            if attr != "availableDiskSpace"
        }

    @backoff.on_exception(
        backoff.expo,
        AssertionError,
        factor=0.05,
        max_time=1.0,
    )
    def assert_admin_mode(self: TestPstBeam, admin_mode: AdminMode) -> None:
        """Assert admin mode of devices."""
        assert self.beam_proxy.adminMode == admin_mode
        assert self.recv_proxy.adminMode == admin_mode
        assert self.smrb_proxy.adminMode == admin_mode
        assert self.dsp_proxy.adminMode == admin_mode

    def assert_state(self: TestPstBeam, state: DevState) -> None:
        """Assert device state of devices."""
        assert self.beam_proxy.state() == state
        assert self.recv_proxy.state() == state
        assert self.smrb_proxy.state() == state
        assert self.dsp_proxy.state() == state

    def assert_health_state(self: TestPstBeam, health_state: HealthState) -> None:
        """Assert health state of devices."""
        assert self.beam_proxy.healthState == health_state
        assert self.recv_proxy.healthState == health_state
        assert self.smrb_proxy.healthState == health_state
        assert self.dsp_proxy.healthState == health_state

    @backoff.on_exception(
        backoff.expo,
        AssertionError,
        factor=0.05,
        max_time=1.0,
    )
    def assert_obs_state(
        self: TestPstBeam, obsState: ObsState, subObsState: Optional[ObsState] = None
    ) -> None:
        """Assert the observation state of devices."""
        assert self.beam_proxy.obsState == obsState

        if subObsState is not None:
            assert self.recv_proxy.obsState == subObsState
            assert self.smrb_proxy.obsState == subObsState
            assert self.dsp_proxy.obsState == subObsState
        else:
            assert self.recv_proxy.obsState == obsState
            assert self.smrb_proxy.obsState == obsState
            assert self.dsp_proxy.obsState == obsState

    def configure_scan(self: TestPstBeam, configuration: str) -> None:
        """Perform a configure scan."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )
        self.assert_obs_state(ObsState.READY)

    def scan(self: TestPstBeam, scan_id: str) -> None:
        """Perform a scan."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.Scan(scan_id),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )
        self.assert_obs_state(ObsState.SCANNING)

    def end_scan(self: TestPstBeam) -> None:
        """End current scan."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.EndScan(),
            expected_obs_state_events=[
                ObsState.READY,
            ],
        )
        self.assert_obs_state(ObsState.READY)

    def goto_idle(self: TestPstBeam) -> None:
        """Put Tango device into IDLE state."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.GoToIdle(),
            expected_obs_state_events=[
                ObsState.IDLE,
            ],
        )
        self.assert_obs_state(ObsState.IDLE, subObsState=ObsState.EMPTY)

    def abort(self: TestPstBeam) -> None:
        """Abort long running command."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.Abort(),
            expected_result_code=ResultCode.STARTED,
            expected_obs_state_events=[
                ObsState.ABORTING,
                ObsState.ABORTED,
            ],
        )

    def goto_fault(self: TestPstBeam, fault_msg: str) -> None:
        """Force device to go to fault."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.GoToFault(fault_msg),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        self.assert_obs_state(ObsState.FAULT)
        assert self.beam_proxy.healthFailureMessage == fault_msg
        assert self.beam_proxy.healthState == HealthState.FAILED

    def obs_reset(self: TestPstBeam) -> None:
        """Reset Tango device."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
        )
        self.assert_obs_state(ObsState.IDLE, subObsState=ObsState.EMPTY)

    def on(self: TestPstBeam) -> None:
        """Turn on Tango device."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.On(), expected_obs_state_events=[ObsState.IDLE]
        )
        self.assert_state(DevState.ON)

        # need to configure beam
        self.assert_obs_state(ObsState.IDLE, subObsState=ObsState.EMPTY)

    def off(self: TestPstBeam) -> None:
        """Turn off Tango device."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.Off(),
        )
        self.assert_state(DevState.OFF)
        self.assert_health_state(HealthState.OK)

    def online(self: TestPstBeam) -> None:
        """Put Tango device into ONLINE mode."""
        self.beam_proxy.adminMode = AdminMode.ONLINE
        self.assert_admin_mode(admin_mode=AdminMode.ONLINE)
        self.assert_state(DevState.OFF)
        self.assert_health_state(HealthState.OK)

    def offline(self: TestPstBeam) -> None:
        """Put Tango device into OFFLINE mode."""
        self.beam_proxy.adminMode = AdminMode.OFFLINE
        self.assert_admin_mode(admin_mode=AdminMode.OFFLINE)
        self.assert_state(DevState.DISABLE)
        self.assert_health_state(HealthState.UNKNOWN)

    def test_beam_mgmt_State(self: TestPstBeam, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        device_under_test.adminMode = AdminMode.ONLINE
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
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
    ) -> None:
        """Test state model of PstBeam can configure, scan and stop."""
        # need to go through state mode
        self.assert_health_state(HealthState.UNKNOWN)

        self.online()
        self.on()

        configuration = json.dumps(csp_configure_scan_request)
        self.configure_scan(configuration)

        scan = str(scan_id)
        self.scan(scan)
        self.end_scan()
        self.goto_idle()
        self.off()
        self.offline()

    def test_beam_mgmt_configure_when_validation_error(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
    ) -> None:
        """Test state model of PstBeam can configure, scan and stop."""
        # need to go through state mode
        self.assert_health_state(HealthState.UNKNOWN)

        self.online()
        self.on()

        csp_configure_scan_request["pst"]["scan"]["source"] = "invalid source"
        configuration = json.dumps(csp_configure_scan_request)

        ([result], [msg]) = self.beam_proxy.ConfigureScan(configuration)

        assert result == ResultCode.FAILED
        assert msg == "Simulated validation error due to invalid source"

        self.off()
        self.offline()

    def test_beam_mgmt_abort(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
    ) -> None:
        """Test PstBeam can abort."""
        self.assert_health_state(HealthState.UNKNOWN)
        self.online()
        self.on()

        configuration = json.dumps(csp_configure_scan_request)
        self.configure_scan(configuration)

        scan = str(scan_id)
        self.scan(scan)

        self.abort()
        self.obs_reset()

        self.off()
        self.offline()

    def test_beam_mgmt_go_to_fault(
        self: TestPstBeam,
    ) -> None:
        """Test state model of PstBeam and go to Fault state."""
        self.assert_health_state(HealthState.UNKNOWN)
        self.online()
        self.on()

        self.goto_fault("this is a fault message")

        self.obs_reset()
        self.off()
        self.offline()

    @pytest.mark.forked
    def test_beam_mgmt_scan_monitoring_values(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_change_event_helper: TangoChangeEventHelper,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger,
        default_device_propertry_config: Dict[str, Dict[str, Any]],
    ) -> None:
        """Test that monitoring values are updated."""
        self.assert_health_state(HealthState.UNKNOWN)

        self.online()

        attribute_event_validators = [
            _AttributeEventValidator(
                device_under_test=self.beam_proxy,
                source_device_fqdn=fqdn,
                attribute_name=attribute_name,
                default_value=default_value,
                tango_change_event_helper=tango_change_event_helper,
                change_event_callbacks=change_event_callbacks,
                logger=logger,
            )
            for fqdn, props in default_device_propertry_config.items()
            for attribute_name, default_value in props.items()
        ]

        self.on()

        # assert initial values.
        for v in attribute_event_validators:
            v.assert_initial_values()

        # need to set up scanning
        configuration = json.dumps(csp_configure_scan_request)
        self.configure_scan(configuration)

        scan = str(scan_id)
        self.scan(scan)

        # wait for a monitoring period?
        time.sleep(0.25)

        self.end_scan()

        # Assert attribute values
        for v in attribute_event_validators:
            v.assert_values()

        self.scan(scan)

        # wait for a monitoring period?
        time.sleep(0.25)

        self.end_scan()

        for v in attribute_event_validators:
            v.assert_values()

    @pytest.mark.forked
    def test_beam_mgmt_resubscribes_to_device_events(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_change_event_helper: TangoChangeEventHelper,
        change_event_callbacks_factory: Callable[..., MockTangoEventCallbackGroup],
        logger: logging.Logger,
        default_device_propertry_config: Dict[str, Dict[str, Any]],
    ) -> None:
        """Test that monitoring values are updated."""
        self.assert_health_state(HealthState.UNKNOWN)

        self.online()

        init_attr_values = self.current_attribute_values()
        self.on()

        # need to set up scanning
        configuration = json.dumps(csp_configure_scan_request)
        self.configure_scan(configuration)

        scan = str(scan_id)
        self.scan(scan)

        # assert that the attribute values have been updated during monitoring
        assert init_attr_values != self.current_attribute_values()

        # wait for a monitoring period?
        time.sleep(0.25)

        self.end_scan()

        self.goto_idle()
        self.off()

        # assert the attribute values are reset when in Off state
        assert init_attr_values == self.current_attribute_values()

        self.on()

        configuration = json.dumps(csp_configure_scan_request)
        self.configure_scan(configuration)

        scan = str(scan_id + 1)
        self.scan(scan)

        time.sleep(0.25)

        # assert that the attribute values have been updated during monitoring
        assert init_attr_values != self.current_attribute_values()

        self.end_scan()

        self.goto_idle()
        self.off()

        assert init_attr_values == self.current_attribute_values()

    @pytest.mark.forked
    def test_beam_mgmt_ends_in_fault_state_when_subordinate_device_ends_up_in_fault_state(
        self: TestPstBeam,
        change_event_callbacks: MockTangoEventCallbackGroup,
    ) -> None:
        """Test state model of PstBeam ends up in FAULT when subordinate device faults."""
        import random

        self.assert_health_state(HealthState.UNKNOWN)
        self.online()
        self.on()
        change_event_callbacks["healthState"].assert_change_event(HealthState.OK)

        rand_device_id = random.randint(0, 2)
        if rand_device_id == 0:
            subdevice = self.dsp_proxy
        elif rand_device_id == 1:
            subdevice = self.recv_proxy
        else:
            subdevice = self.smrb_proxy
        fault_msg = f"putting {subdevice.dev_name()} into FAULT"

        subdevice.GoToFault(fault_msg)

        # expect - beam.obsState ends up as fault
        change_event_callbacks["obsState"].assert_change_event(ObsState.FAULT)
        change_event_callbacks["healthState"].assert_change_event(HealthState.FAILED)

        assert self.beam_proxy.healthFailureMessage == fault_msg
        assert self.beam_proxy.healthState == HealthState.FAILED
