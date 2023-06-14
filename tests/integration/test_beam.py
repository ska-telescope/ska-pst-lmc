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
import time
from typing import Any, Dict, List, Optional

import backoff
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, ObsState, SimulationMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState

from ska_pst_lmc import DeviceProxyFactory
from tests.conftest import TangoChangeEventHelper, TangoDeviceCommandChecker


@pytest.fixture
def additional_change_events_callbacks(beam_attribute_names: List[str]) -> List[str]:
    """Return additional change event callbacks."""
    return [*beam_attribute_names]


@pytest.fixture
def change_event_callback_time() -> float:
    """Get timeout used for change event callbacks."""
    return 5.0


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
                "num_frequency_channels": int(432 / scan_id),
                "max_scan_length": 300.0 / scan_id,
                "total_bandwidth": 1562500.0 * scan_id,
            }

    return scan_configs


@pytest.mark.integration
class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture(autouse=True)
    def setup_test_class(
        self: TestPstBeam,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger,
        beam_attribute_names: List[str],
    ) -> None:
        """Put test class with Tango devices and event checker."""
        self.dsp_proxy = DeviceProxyFactory.get_device("low-pst/dsp/01")
        self.recv_proxy = DeviceProxyFactory.get_device("low-pst/recv/01")
        self.smrb_proxy = DeviceProxyFactory.get_device("low-pst/smrb/01")
        self.beam_proxy = DeviceProxyFactory.get_device("low-pst/beam/01")
        self.logger = logger
        self._beam_attribute_names = beam_attribute_names

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

    def current_attribute_values(self: TestPstBeam) -> Dict[str, Any]:
        """Get current attributate values for BEAM device."""
        # ignore availableDiskSpace as this can change but other props
        # will should get reset when going to Off
        return {
            attr: getattr(self.beam_proxy, attr)
            for attr in self._beam_attribute_names
            if attr not in ["availableDiskSpace", "diskCapacity", "diskUsedPercentage", "diskUsedBytes"]
        }

    def assert_attribute_values(
        self: TestPstBeam,
        prev_attr_values: Dict[str, Any],
        assert_equal: bool = True,
        ignore_channel_bock_config: bool = False,
    ) -> None:
        """Assert whether the current and previous attribute values are equal or not."""
        from copy import deepcopy

        curr_attr_values = self.current_attribute_values()
        if ignore_channel_bock_config:
            prev_attr_values = deepcopy(prev_attr_values)
            del prev_attr_values["channelBlockConfiguration"]
            del curr_attr_values["channelBlockConfiguration"]

        if assert_equal:
            assert prev_attr_values == curr_attr_values
        else:
            assert prev_attr_values != curr_attr_values

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
        max_time=5.0,
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
        max_time=5.0,
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

    # @pytest.mark.forked
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

    # @pytest.mark.forked
    @pytest.mark.skip
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

    # @pytest.mark.forked
    @pytest.mark.skip
    def test_abort_long_running_command(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_id: int,
    ) -> None:
        """Test PstBeam can abort long running command, like scan."""
        import time

        try:
            self.setup_test_state()
            self.assert_state(DevState.DISABLE)

            self.online()
            self.beam_proxy.simulationMode = SimulationMode.TRUE
            self.on()

            configuration = json.dumps(csp_configure_scan_request)
            self.configure_scan(configuration)
            self.scan(str(scan_id))
            time.sleep(2.0)
            self.abort()
            self.obs_reset()

            self.off()
            self.offline()
        except Exception:
            self.logger.exception("Error in trying test_abort_long_running_command.", exc_info=False)

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

    # @pytest.mark.forked
    @pytest.mark.skip
    def test_multiple_lifecycles_with_monitoring(
        self: TestPstBeam,
        csp_configure_scan_request: Dict[str, Any],
        scan_configs: Dict[int, dict],
        monitor_polling_rate_ms: int,
    ) -> None:
        """Test state model of PstBeam with multiple scans."""
        try:
            self.setup_test_state()
            self.assert_state(DevState.DISABLE)

            self.online()
            self.beam_proxy.simulationMode = SimulationMode.TRUE
            prev_attr_values = self.current_attribute_values()
            for (scan_id, scan_config) in scan_configs.items():
                self.on()

                self.logger.info(f"Performing scan {scan_id} with overridden config of {scan_config}")
                csp_configure_scan_request["pst"]["scan"] = {
                    **csp_configure_scan_request["pst"]["scan"],
                    **scan_config,
                }
                configuration = json.dumps(csp_configure_scan_request)
                self.configure_scan(configuration)
                self.scan(str(scan_id))

                # need to wait 2 polling periods - set to being 500ms in test-parent
                time.sleep(2 * monitor_polling_rate_ms / 1000.0)

                # assert that a scan will update values
                self.assert_attribute_values(prev_attr_values, assert_equal=False)

                self.end_scan()

                # ending a scan will stop monitoring
                prev_attr_values = self.current_attribute_values()

                self.goto_idle()
                self.off()

                # as monitoring had stopped there should be no update of values
                self.assert_attribute_values(prev_attr_values, ignore_channel_bock_config=True)
                prev_attr_values = self.current_attribute_values()

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
