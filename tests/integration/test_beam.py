# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains pytests for integration tests."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import backoff
import pytest
from ska_tango_base.control_model import AdminMode, ObsState, SimulationMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_pst_lmc import DeviceProxyFactory
from tests.conftest import TangoChangeEventHelper, TangoDeviceCommandChecker


@pytest.fixture
def num_scan_configs() -> int:
    """Get number of scan configurations to create."""
    return 3


@pytest.fixture
def scan_configs(num_scan_configs: int) -> Dict[int, dict]:
    """Get scan configurations."""
    scan_configs: Dict[int, dict] = {}

    for scan_id in range(1, num_scan_configs + 1):
        if scan_id == 1:
            scan_configs[scan_id] = {}
        else:
            # add some different values - for this test we're expecting to be in simulation mode.
            scan_configs[scan_id] = {
                "centre_frequency": 1000000000.0 * scan_id,
                "num_frequency_channels": 432 * scan_id,
                "max_scan_length": 300.0 * scan_id,
                "total_bandwidth": 1562500.0 * scan_id,
            }

    return scan_configs


@pytest.mark.integration
class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture(autouse=True)
    def setup_test_class(
        self: TestPstBeam, change_event_callbacks: MockTangoEventCallbackGroup, logger: logging.Logger
    ) -> None:
        """Put test class with Tango devices and event checker."""
        self.dsp_proxy = DeviceProxyFactory.get_device("low-pst/dsp/01")
        self.recv_proxy = DeviceProxyFactory.get_device("low-pst/recv/01")
        self.smrb_proxy = DeviceProxyFactory.get_device("low-pst/smrb/01")
        self.beam_proxy = DeviceProxyFactory.get_device("low-pst/beam/01")
        self.logger = logger

        self.tango_change_event_helper = TangoChangeEventHelper(
            device_under_test=self.beam_proxy.device,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

        self.tango_device_command_checker = TangoDeviceCommandChecker(
            tango_change_event_helper=self.tango_change_event_helper,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

    def configure_scan(self: TestPstBeam, configuration: str) -> None:
        """Perform a configure scan."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )
        self.assert_obstate(ObsState.READY)

    def scan(self: TestPstBeam, scan_id: str) -> None:
        """Perform a scan."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.Scan(scan_id),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )
        self.assert_obstate(ObsState.SCANNING)

    def end_scan(self: TestPstBeam) -> None:
        """End current scan."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.EndScan(),
            expected_obs_state_events=[
                ObsState.READY,
            ],
        )
        self.assert_obstate(ObsState.READY)

    def goto_idle(self: TestPstBeam) -> None:
        """Put Tango device into IDLE state."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.GoToIdle(),
            expected_obs_state_events=[
                ObsState.IDLE,
            ],
        )
        self.assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

    def obs_reset(self: TestPstBeam) -> None:
        """Reset Tango device."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
        )
        self.assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

    def on(self: TestPstBeam) -> None:
        """Turn on Tango device."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.On(), expected_obs_state_events=[ObsState.IDLE]
        )
        self.assert_state(DevState.ON)

        # need to configure beam
        self.assert_obstate(ObsState.IDLE, subObsState=ObsState.EMPTY)

    def off(self: TestPstBeam) -> None:
        """Turn off Tango device."""
        self.tango_device_command_checker.assert_command(
            lambda: self.beam_proxy.Off(),
        )
        self.assert_state(DevState.OFF)

    def online(self: TestPstBeam) -> None:
        """Put Tango device into ONLINE mode."""
        self.beam_proxy.adminMode = AdminMode.ONLINE
        self.assert_admin_mode(admin_mode=AdminMode.ONLINE)
        self.assert_state(DevState.OFF)

    def offline(self: TestPstBeam) -> None:
        """Put Tango device into OFFLINE mode."""
        self.beam_proxy.adminMode = AdminMode.OFFLINE
        self.assert_admin_mode(admin_mode=AdminMode.OFFLINE)
        self.assert_state(DevState.DISABLE)

    def setup_test_state(self: TestPstBeam) -> None:
        """Ensure Tango device is in Offline mode before test executes."""
        if self.beam_proxy.obsState in [ObsState.ABORTED, ObsState.FAULT]:
            self.logger.info(f"{self.beam_proxy} is in obsState {self.beam_proxy.obsState}. Calling ObsReset")
            self.obs_reset()

        if self.beam_proxy.obsState == ObsState.SCANNING:
            self.logger.info(f"{self.beam_proxy} is SCANNING. Calling EndScan")
            self.end_scan()

        if self.beam_proxy.obsState == ObsState.READY:
            self.logger.info(f"{self.beam_proxy} is READY. Calling GoToIdle")
            self.goto_idle()

        if self.beam_proxy.state() == DevState.ON:
            self.logger.info(f"{self.beam_proxy} is in DevState.ON. Calling Off")
            self.off()

        if self.beam_proxy.state() == DevState.OFF:
            self.logger.info(f"{self.beam_proxy} is in DevState.OFF. Setting it to OFFLINE")
            self.offline()

    @backoff.on_exception(
        backoff.expo,
        AssertionError,
        factor=0.05,
        max_time=1.0,
    )
    def assert_state(self: TestPstBeam, state: DevState) -> None:
        """Assert Tango devices are in a given DevState."""
        assert self.beam_proxy.state() == state
        assert self.recv_proxy.state() == state
        assert self.smrb_proxy.state() == state
        assert self.dsp_proxy.state() == state

    @backoff.on_exception(
        backoff.expo,
        AssertionError,
        factor=0.05,
        max_time=1.0,
    )
    def assert_obstate(self: TestPstBeam, obsState: ObsState, subObsState: Optional[ObsState] = None) -> None:
        """Assert that the Tango devices are in a giveen ObsState."""
        assert self.beam_proxy.obsState == obsState
        assert self.recv_proxy.obsState == subObsState or obsState
        assert self.smrb_proxy.obsState == subObsState or obsState
        assert self.dsp_proxy.obsState == subObsState or obsState

    @backoff.on_exception(
        backoff.expo,
        AssertionError,
        factor=1,
        max_time=5.0,
    )
    def assert_admin_mode(self: TestPstBeam, admin_mode: AdminMode) -> None:
        """Assert that the Tango devices are in a given AdminMode."""
        assert self.beam_proxy.adminMode == admin_mode
        assert self.recv_proxy.adminMode == admin_mode
        assert self.smrb_proxy.adminMode == admin_mode
        assert self.dsp_proxy.adminMode == admin_mode

    @pytest.mark.forked
    def test_configure_then_scan_then_stop(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
    ) -> None:
        """Test state model of PstBeam."""
        try:
            self.setup_test_state()
            self.assert_state(DevState.DISABLE)

            self.online()
            self.beam_proxy.simulationMode = SimulationMode.TRUE
            self.on()

            configuration = json.dumps(csp_configure_scan_request)
            self.configure_scan(configuration)
            self.scan(str(scan_id))
            self.end_scan()
            self.goto_idle()
            self.off()
            self.offline()
        except Exception:
            self.logger.exception("Error in trying test_configure_then_scan_then_stop.", exc_info=False)

            for p in [
                "longRunningCommandStatus",
                "longRunningCommandResult",
                "obsState",
                "adminMode",
                "state()",
            ]:
                for d in [self.beam_proxy, self.dsp_proxy, self.recv_proxy, self.smrb_proxy]:
                    if p == "state()":
                        self.logger.info(f"{d}.{p} = {d.state()}")
                    else:
                        if d.state() != DevState.DISABLE:
                            self.logger.info(f"{d}.{p} = {getattr(d, p)}")

            raise
        finally:
            self.tango_change_event_helper.release()

    @pytest.mark.forked
    def test_multiple_scans(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_configs: Dict[int, dict],
    ) -> None:
        """Test state model of PstBeam with multiple scans."""
        try:
            self.setup_test_state()
            self.assert_state(DevState.DISABLE)

            self.online()
            self.beam_proxy.simulationMode = SimulationMode.TRUE
            self.on()

            for (scan_id, scan_config) in scan_configs.items():
                self.logger.info(f"Performing scan {scan_id} with overridden config of {scan_config}")
                csp_configure_scan_request["pst"]["scan"] = {
                    **csp_configure_scan_request["pst"]["scan"],
                    **scan_config,
                }
                configuration = json.dumps(csp_configure_scan_request)
                self.configure_scan(configuration)
                self.scan(str(scan_id))
                self.end_scan()
                self.goto_idle()
            self.off()
            self.offline()
        except Exception:
            self.logger.exception("Error in trying test_configure_then_scan_then_stop.", exc_info=False)

            for p in [
                "longRunningCommandStatus",
                "longRunningCommandResult",
                "obsState",
                "adminMode",
                "state()",
            ]:
                for d in [self.beam_proxy, self.dsp_proxy, self.recv_proxy, self.smrb_proxy]:
                    if p == "state()":
                        self.logger.info(f"{d}.{p} = {d.state()}")
                    else:
                        if d.state() != DevState.DISABLE:
                            self.logger.info(f"{d}.{p} = {getattr(d, p)}")

            raise
        finally:
            self.tango_change_event_helper.release()
