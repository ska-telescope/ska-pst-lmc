# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Test to the DSP Tango device for PST.LMC."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Type

import numpy as np
import pytest
import tango
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_base.control_model import AdminMode, HealthState, ObsState, SimulationMode
from tango import DeviceProxy, DevState

from ska_pst_lmc.dsp.dsp_component_manager import PstDspComponentManager
from ska_pst_lmc.dsp.dsp_device import PstDsp
from tests.conftest import TangoDeviceCommandChecker


@pytest.fixture
def monitor_polling_rate() -> int:
    """Fixture to get monitoring polling rate for test."""
    return 100


@pytest.fixture
def device_properties(
    grpc_endpoint: str,
    monitor_polling_rate: int,
) -> dict:
    """Fixture that returns device_properties to be provided to the device under test."""
    return {
        "process_api_endpoint": grpc_endpoint,
        "monitor_polling_rate": monitor_polling_rate,
    }


@pytest.fixture
def dsp_device_class(logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> Type[PstDsp]:
    """Get PstDsp fixture.

    This creates a subclass of the PstDsp that overrides the create_component_manager method
    to use the component_manager fixture.
    """

    def _update_api(*args: Any, **kwargs: Any) -> None:
        pass

    monkeypatch.setattr(PstDspComponentManager, "_update_api", _update_api)

    class _PstDsp(PstDsp):
        def create_component_manager(self: _PstDsp) -> PstDspComponentManager:
            return PstDspComponentManager(device_interface=self, logger=logger)

    return _PstDsp


@pytest.mark.forked
class TestPstDsp:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture
    def device_test_config(
        self: TestPstDsp,
        device_properties: dict,
        dsp_device_class: Type[PstDsp],
    ) -> dict:
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
            "device": dsp_device_class,
            "process": False,
            "properties": device_properties,
            "memorized": {"adminMode": str(AdminMode.ONLINE.value)},
        }

    def test_dsp_mgmt_State(self: TestPstDsp, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_dsp_mgmt_GetVersionInfo(self: TestPstDsp, device_under_test: DeviceProxy) -> None:
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

    def test_dsp_mgmt_configure_then_scan_then_stop(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstDsp."""
        # need to have this in OFFLINE mode to start with to assert unknown health state
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.healthState == HealthState.UNKNOWN

        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.healthState == HealthState.OK
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON
        assert device_under_test.healthState == HealthState.OK

        resources = json.dumps(configure_beam_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureBeam(resources),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.IDLE,
            ],
        )

        configuration = json.dumps(configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Scan(str(scan_id)),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )

        # still need to sleep. Wait for 2 polling periods
        time.sleep(0.2)
        assert device_under_test.diskCapacity > 0
        assert device_under_test.availableDiskSpace > 0
        assert device_under_test.diskUsedBytes > 0
        assert (
            device_under_test.diskCapacity
            == device_under_test.availableDiskSpace + device_under_test.diskUsedBytes
        )
        assert device_under_test.diskUsedPercentage >= 0.0
        np.testing.assert_almost_equal(
            device_under_test.diskUsedPercentage,
            100.0 * device_under_test.diskUsedBytes / device_under_test.diskCapacity,
        )
        assert device_under_test.dataRecordRate >= 0.0
        assert device_under_test.dataRecorded > 0

        for wr in device_under_test.subbandDataRecordRate:
            assert wr >= 0.0

        for bw in device_under_test.subbandDataRecorded:
            assert bw > 0

        assert device_under_test.dataRecorded == np.sum(device_under_test.subbandDataRecorded)
        np.testing.assert_almost_equal(
            device_under_test.dataRecordRate, np.sum(device_under_test.dataRecordRate)
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.EndScan(),
            expected_obs_state_events=[
                ObsState.READY,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToIdle(),
            expected_obs_state_events=[
                ObsState.IDLE,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.DeconfigureBeam(),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.EMPTY,
            ],
        )

        tango_device_command_checker.assert_command(lambda: device_under_test.Off())
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.healthState == HealthState.OK

        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.healthState == HealthState.UNKNOWN

    def test_dsp_mgmt_abort_when_scanning(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is SCANNING and abort is requested."""
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(configure_beam_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureBeam(resources),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.IDLE,
            ],
        )

        configuration = json.dumps(configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Scan(str(scan_id)),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Abort(),
            expected_result_code=ResultCode.STARTED,
            expected_command_status_events=[
                TaskStatus.IN_PROGRESS,
                TaskStatus.COMPLETED,
            ],
            expected_obs_state_events=[
                ObsState.ABORTING,
                ObsState.ABORTED,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
        )

        configuration = json.dumps(configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Scan(str(scan_id)),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Abort(),
            expected_result_code=ResultCode.STARTED,
            expected_command_status_events=[
                TaskStatus.IN_PROGRESS,
                TaskStatus.COMPLETED,
            ],
            expected_obs_state_events=[
                ObsState.ABORTING,
                ObsState.ABORTED,
            ],
        )

    def test_dsp_mgmt_simulation_mode(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
    ) -> None:
        """Test state model of PstDsp."""
        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

    def test_dsp_mgmt_simulation_mode_when_not_in_empty_obs_state(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstDsp."""
        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.adminMode = AdminMode.ONLINE
        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(configure_beam_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureBeam(resources),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.IDLE,
            ],
        )
        assert device_under_test.obsState == ObsState.IDLE

        with pytest.raises(tango.DevFailed) as exc_info:
            device_under_test.simulationMode = SimulationMode.FALSE

        assert device_under_test.simulationMode == SimulationMode.TRUE
        exc_info.value.args[
            0
        ].desc == "ValueError: Unable to change simulation mode unless in EMPTY observation state"

    def test_dsp_mgmt_simulation_mode_when_in_empty_obs_state(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstDsp."""
        assert device_under_test.obsState == ObsState.EMPTY

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.adminMode = AdminMode.ONLINE
        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON

        assert device_under_test.state() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE

    def test_dsp_mgmt_go_to_fault_when_beam_configured(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is in IDLE state and GoToFault is called."""
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(configure_beam_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureBeam(resources),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.IDLE,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToFault("putting DSP.MGMT into FAULT"),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert device_under_test.healthFailureMessage == "putting DSP.MGMT into FAULT"
        assert device_under_test.healthState == HealthState.FAILED

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
        )

    def test_dsp_mgmt_go_to_fault_when_configured(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is READY state and GoToFault is called."""
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(configure_beam_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureBeam(resources),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.IDLE,
            ],
        )

        configuration = json.dumps(configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToFault("putting DSP.MGMT into FAULT"),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert device_under_test.healthFailureMessage == "putting DSP.MGMT into FAULT"
        assert device_under_test.healthState == HealthState.FAILED

    def test_dsp_mgmt_go_to_fault_when_scanning(
        self: TestPstDsp,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is SCANNING and GoToFault is called."""
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(configure_beam_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureBeam(resources),
            expected_obs_state_events=[
                ObsState.RESOURCING,
                ObsState.IDLE,
            ],
        )

        configuration = json.dumps(configure_scan_request)
        tango_device_command_checker.assert_command(
            lambda: device_under_test.ConfigureScan(configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.Scan(str(scan_id)),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToFault("putting DSP.MGMT into FAULT"),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert device_under_test.healthFailureMessage == "putting DSP.MGMT into FAULT"
        assert device_under_test.healthState == HealthState.FAILED
