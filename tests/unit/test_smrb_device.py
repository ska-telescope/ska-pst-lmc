# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Test to the SMRB TANGO device for PST.LMC."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Type, cast

import pytest
import tango
from ska_pst_testutils.tango import TangoDeviceCommandChecker
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_base.control_model import AdminMode, HealthState, ObsState, SimulationMode
from tango import DeviceProxy, DevState

from ska_pst_lmc.smrb import PstSmrbComponentManager, PstSmrbProcessApiSimulator
from ska_pst_lmc.smrb.smrb_device import PstSmrb


@pytest.fixture
def device_properties(
    grpc_endpoint: str,
    monitoring_polling_rate: int,
    subsystem_id: str,
) -> dict:
    """Fixture that returns device_properties to be provided to the device under test."""
    return {
        "process_api_endpoint": grpc_endpoint,
        "initial_monitoring_polling_rate": monitoring_polling_rate,
        "SubsystemId": subsystem_id,
    }


@pytest.fixture
def smrb_device_class(
    logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
    fail_validate_configure_beam: bool,
    fail_validate_configure_scan: bool,
) -> Type[PstSmrb]:
    """
    Get PstSmrb fixture.

    This creates a subclass of the PstSmrb that overrides the create_component_manager method to use the
    component_manager fixture.
    """

    def _update_api(*args: Any, **kwargs: Any) -> None:
        pass

    monkeypatch.setattr(PstSmrbComponentManager, "_update_api", _update_api)

    class _PstSmrb(PstSmrb):
        def create_component_manager(self: _PstSmrb) -> PstSmrbComponentManager:
            cm = PstSmrbComponentManager(
                device_interface=self,
                logger=logger,
            )
            cast(
                PstSmrbProcessApiSimulator, cm._api
            ).fail_validate_configure_beam = fail_validate_configure_beam
            cast(
                PstSmrbProcessApiSimulator, cm._api
            ).fail_validate_configure_scan = fail_validate_configure_scan

            return cm

    return _PstSmrb


@pytest.mark.forked
class TestPstSmrb:
    """Test class used for testing the PstSmrb TANGO device."""

    @pytest.fixture
    def device_test_config(
        self: TestPstSmrb,
        device_properties: dict,
        smrb_device_class: Type[PstSmrb],
    ) -> dict:
        """
        Specify device configuration, including properties and memorized attributes.

        This implementation provides a concrete subclass of SKABaseDevice, and a memorized value for
        adminMode.

        :param device_properties: fixture that returns device properties of the device under test
        :return: specification of how the device under test should be configured
        """
        return {
            "device": smrb_device_class,
            "process": False,
            "properties": device_properties,
            "memorized": {"adminMode": str(AdminMode.ONLINE.value)},
        }

    def test_smrb_mgmt_State(self: TestPstSmrb, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_smrb_mgmt_GetVersionInfo(self: TestPstSmrb, device_under_test: DeviceProxy) -> None:
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

    def test_smrb_mgmt_validate_configure_scan(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        configure_scan_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test the ValidateConfigureScan passes validation."""
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.healthState == HealthState.UNKNOWN

        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.healthState == HealthState.OK
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON
        resources = json.dumps(configure_scan_request)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ValidateConfigureScan(resources),
        )

    @pytest.mark.parametrize("fail_validate_configure_beam", [True])
    def test_smrb_mgmt_validate_configure_scan_fails_beam_configuration_validation(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        configure_scan_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test the ValidateConfigureScan when beam configuration fails validation."""
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.healthState == HealthState.UNKNOWN

        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.healthState == HealthState.OK
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON
        resources = json.dumps(configure_scan_request)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ValidateConfigureScan(resources),
            expected_command_result="Simulated validation error for configure beam.",
            expected_command_status_events=[
                TaskStatus.QUEUED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.FAILED,
            ],
        )

    @pytest.mark.parametrize("fail_validate_configure_scan", [True])
    def test_smrb_mgmt_validate_configure_scan_fails_scan_configuration_validation(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        configure_scan_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test the ValidateConfigureScan when scan configuration fails validation."""
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.healthState == HealthState.UNKNOWN

        device_under_test.adminMode = AdminMode.ONLINE
        assert device_under_test.healthState == HealthState.OK
        assert device_under_test.state() == DevState.OFF

        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON
        resources = json.dumps(configure_scan_request)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ValidateConfigureScan(resources),
            expected_command_result="Simulated validation error for configure scan.",
            expected_command_status_events=[
                TaskStatus.QUEUED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.FAILED,
            ],
        )

    def test_smrb_mgmt_configure_then_scan_then_stop(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstSmrb."""
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
        assert device_under_test.ringBufferUtilisation >= 0.0
        assert device_under_test.ringBufferSize > 0
        assert device_under_test.numberSubbands > 0
        assert device_under_test.ringBufferRead >= 0
        assert device_under_test.ringBufferWritten >= 0

        for i in range(device_under_test.numberSubbands):
            assert device_under_test.subbandRingBufferUtilisations[i] >= 0.0
            assert device_under_test.subbandRingBufferSizes[i] > 0
            assert device_under_test.subbandRingBufferRead[i] >= 0
            assert device_under_test.subbandRingBufferWritten[i] >= 0

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

    def test_smrb_mgmt_abort_when_scanning(
        self: TestPstSmrb,
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
                ObsState.EMPTY,
            ],
        )

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

    def test_smrb_mgmt_simulation_mode(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
    ) -> None:
        """Test state model of PstSmrb."""
        device_under_test.loggingLevel = 5

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

    def test_smrb_mgmt_simulation_mode_when_not_in_empty_obs_state(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstSmrb."""
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

    def test_smrb_mgmt_simulation_mode_when_in_empty_obs_state(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstSmrb."""
        assert device_under_test.obsState == ObsState.EMPTY

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.adminMode = AdminMode.ONLINE
        tango_device_command_checker.assert_command(
            lambda: device_under_test.On(), expected_obs_state_events=[ObsState.EMPTY]
        )
        assert device_under_test.state() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE

    def test_smrb_mgmt_go_to_fault_when_beam_configured(
        self: TestPstSmrb,
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
            lambda: device_under_test.GoToFault("putting SMRB.MGMT into FAULT"),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert device_under_test.healthFailureMessage == "putting SMRB.MGMT into FAULT"
        assert device_under_test.healthState == HealthState.FAILED

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.EMPTY,
            ],
        )

    def test_smrb_mgmt_go_to_fault_when_configured(
        self: TestPstSmrb,
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
            lambda: device_under_test.GoToFault("putting SMRB.MGMT into FAULT"),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert device_under_test.healthFailureMessage == "putting SMRB.MGMT into FAULT"
        assert device_under_test.healthState == HealthState.FAILED

    def test_smrb_mgmt_go_to_fault_when_scanning(
        self: TestPstSmrb,
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
            lambda: device_under_test.GoToFault("putting SMRB.MGMT into FAULT"),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
        assert device_under_test.healthFailureMessage == "putting SMRB.MGMT into FAULT"
        assert device_under_test.healthState == HealthState.FAILED
