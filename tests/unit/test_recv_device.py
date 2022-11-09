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
from typing import Any, Dict, Generator
from unittest.mock import MagicMock

import pytest
import tango
from ska_pst_lmc_proto import ConnectionRequest, ConnectionResponse
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_base.control_model import AdminMode, ObsState, SimulationMode
from tango import DeviceProxy, DevState
from tango.test_context import DeviceTestContext

from ska_pst_lmc import PstReceive
from ska_pst_lmc.receive import generate_random_update
from ska_pst_lmc.receive.receive_model import ReceiveData
from ska_pst_lmc.test import TestPstLmcService
from tests.conftest import TangoDeviceCommandChecker


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


@pytest.fixture
def device_properties(
    grpc_endpoint: str,
) -> dict:
    """Fixture that returns device_properties to be provided to the device under test."""
    return {
        "process_api_endpoint": grpc_endpoint,
        "monitor_polling_rate": 100,
    }


class TestPstReceive:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture
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
        assert device_under_test.received_rate > 0.0
        assert device_under_test.received_data > 0
        assert device_under_test.dropped_rate > 0.0
        assert device_under_test.dropped_data > 0
        assert device_under_test.misordered_packets >= 0

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

    @pytest.mark.forked
    def test_recv_abort_when_scanning(
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

    @pytest.mark.forked
    def test_simulation_mode(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        pst_lmc_service: TestPstLmcService,
        mock_servicer_context: MagicMock,
    ) -> None:
        """Test state model of PstReceive."""
        device_under_test.loggingLevel = 5

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        response = ConnectionResponse()
        mock_servicer_context.connect = MagicMock(return_value=response)

        device_under_test.simulationMode = SimulationMode.FALSE
        mock_servicer_context.connect.assert_called_once_with(
            ConnectionRequest(client_id=device_under_test.name())
        )
        assert device_under_test.simulationMode == SimulationMode.FALSE

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

    @pytest.mark.forked
    def test_simulation_mode_when_not_in_empty_obs_state(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        configure_beam_request: Dict[str, Any],
    ) -> None:
        """Test state model of PstReceive."""
        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.adminMode = AdminMode.ONLINE
        device_under_test.On()
        time.sleep(0.1)
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(configure_beam_request)
        device_under_test.ConfigureBeam(resources)
        time.sleep(0.5)
        assert device_under_test.obsState == ObsState.IDLE

        with pytest.raises(tango.DevFailed) as exc_info:
            device_under_test.simulationMode = SimulationMode.FALSE

        assert device_under_test.simulationMode == SimulationMode.TRUE
        exc_info.value.args[
            0
        ].desc == "ValueError: Unable to change simulation mode unless in EMPTY observation state"

    @pytest.mark.forked
    def test_simulation_mode_when_in_empty_obs_state(
        self: TestPstReceive,
        device_under_test: DeviceProxy,
        pst_lmc_service: TestPstLmcService,
        mock_servicer_context: MagicMock,
    ) -> None:
        """Test state model of PstReceive."""
        response = ConnectionResponse()
        mock_servicer_context.connect = MagicMock(return_value=response)
        assert device_under_test.obsState == ObsState.EMPTY

        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.adminMode = AdminMode.ONLINE
        device_under_test.On()
        time.sleep(0.1)
        assert device_under_test.state() == DevState.ON
        assert device_under_test.obsState == ObsState.EMPTY

        device_under_test.simulationMode = SimulationMode.FALSE
        time.sleep(0.1)
        assert device_under_test.simulationMode == SimulationMode.FALSE

    @pytest.mark.forked
    def test_recv_go_to_fault_when_beam_configured(
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

    @pytest.mark.forked
    def test_recv_go_to_fault_when_configured(
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

    @pytest.mark.forked
    def test_recv_go_to_fault_when_scanning(
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

        time.sleep(0.1)

        tango_device_command_checker.assert_command(
            lambda: device_under_test.GoToFault(),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
        )
