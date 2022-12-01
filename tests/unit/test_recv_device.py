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
from typing import Any, Dict, Type
from unittest.mock import MagicMock

import pytest
import tango
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_base.control_model import AdminMode, ObsState, SimulationMode
from tango import DeviceProxy, DevState

from ska_pst_lmc import PstReceive
from ska_pst_lmc.receive import PstReceiveComponentManager
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
def component_manager(
    device_name: str,
    grpc_endpoint: str,
    monitor_polling_rate: int,
    logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
) -> PstReceiveComponentManager:
    """Get fixture for a PstReceiveComponentManager."""
    # monkey patch PstReceiveComponentManager._update_api to do nothing.
    def _update_api(*args: Any, **kwargs: Any) -> None:
        pass

    monkeypatch.setattr(PstReceiveComponentManager, "_update_api", _update_api)

    return PstReceiveComponentManager(
        device_name=device_name,
        process_api_endpoint=grpc_endpoint,
        logger=logger,
        # this is just a place holder to mock these values.
        monitor_data_callback=MagicMock(),
        communication_state_callback=MagicMock(),
        component_state_callback=MagicMock(),
        property_callback=MagicMock(),
        monitor_polling_rate=monitor_polling_rate,
    )


@pytest.fixture
def recv_device_class(component_manager: PstReceiveComponentManager) -> Type[PstReceive]:
    """Get PstReceive fixture.

    This creates a subclass of the PstReceive that overrides the create_component_manager method
    to use the component_manager fixture.
    """

    class _PstReceive(PstReceive):
        def create_component_manager(self: _PstReceive) -> PstReceiveComponentManager:
            component_manager._communication_state_callback = self._communication_state_changed
            component_manager._api._component_state_callback = self._component_state_changed
            component_manager._component_state_callback = self._component_state_changed
            component_manager._monitor_data_handler._monitor_data_callback = self._update_monitor_data
            component_manager._property_callback = self._update_attribute_value

            return component_manager

    return _PstReceive


@pytest.mark.forked
class TestPstReceive:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture
    def device_test_config(
        self: TestPstReceive,
        device_properties: dict,
        recv_device_class: Type[PstReceive],
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
            "device": recv_device_class,
            "process": False,
            "properties": device_properties,
            "memorized": {"adminMode": str(AdminMode.ONLINE.value)},
        }

    def test_recv_mgmt_State(self: TestPstReceive, device_under_test: DeviceProxy) -> None:
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_recv_mgmt_GetVersionInfo(self: TestPstReceive, device_under_test: DeviceProxy) -> None:
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

    def test_recv_mgmt_configure_then_scan_then_stop(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        tango_device_command_checker: TangoDeviceCommandChecker,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_id: int,
    ) -> None:
        """Test state model of PstReceive."""
        # need to go through state mode
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

        # shoud now be able to get some properties
        time.sleep(0.2)
        assert device_under_test.dataReceiveRate > 0.0
        assert device_under_test.receivedData > 0
        assert device_under_test.droppedRate > 0.0
        assert device_under_test.droppedData > 0
        assert device_under_test.misorderedPackets >= 0

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

    def test_recv_mgmt_abort_when_scanning(
        self: TestPstReceive,
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

    def test_recv_mgmt_simulation_mode(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
    ) -> None:
        """Test state model of PstReceive."""
        device_under_test.loggingLevel = 5

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.simulationMode = SimulationMode.FALSE
        assert device_under_test.simulationMode == SimulationMode.FALSE

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

    def test_recv_mgmt_simulation_mode_when_not_in_empty_obs_state(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstReceive."""
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

    def test_recv_mgmt_simulation_mode_when_in_empty_obs_state(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test state model of PstReceive."""
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

    def test_recv_mgmt_go_to_fault_when_beam_configured(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is IDEL and GoToFault is requested."""
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
            lambda: device_under_test.GoToFault(),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )

        tango_device_command_checker.assert_command(
            lambda: device_under_test.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
        )

    def test_recv_mgmt_go_to_fault_when_configured(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is READY and GoToFault is requested."""
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
            lambda: device_under_test.GoToFault(),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )

    def test_recv_mgmt_go_to_fault_when_scanning(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_id: int,
        tango_device_command_checker: TangoDeviceCommandChecker,
    ) -> None:
        """Test that when device is SCANNING and GoToFault is requested."""
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
            lambda: device_under_test.GoToFault(),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
