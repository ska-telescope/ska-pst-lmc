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
from typing import Dict
from unittest.mock import MagicMock

import pytest
import tango
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_tango_base.commands import TaskStatus
from ska_tango_base.control_model import AdminMode, ObsState, SimulationMode
from tango import DeviceProxy, DevState

from ska_pst_lmc.smrb.smrb_device import PstSmrb
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService
from tests.conftest import TangoChangeEventHelper


class TestPstSmrb:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.fixture
    def device_test_config(self: TestPstSmrb, device_properties: dict, grpc_endpoint: str) -> dict:
        """
        Specify device configuration, including properties and memorized attributes.

        This implementation provides a concrete subclass of
        SKABaseDevice, and a memorized value for adminMode.

        :param device_properties: fixture that returns device properties
            of the device under test

        :return: specification of how the device under test should be
            configured
        """
        properties = {
            **device_properties,
            "process_api_endpoint": grpc_endpoint,
            "monitor_polling_rate": 100,
        }
        return {
            "device": PstSmrb,
            "process": True,
            "properties": properties,
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

    @pytest.mark.forked
    def test_configure_then_scan_then_stop(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        assign_resources_request: dict,
        tango_change_event_helper: TangoChangeEventHelper,
    ) -> None:
        """Test state model of PstSmrb."""
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

        resources = json.dumps(assign_resources_request)
        [[result], [command_id]] = device_under_test.AssignResources(resources)

        assert result == TaskStatus.IN_PROGRESS

        assert_command_status(command_id, "QUEUED")
        assert_command_status(command_id, "IN_PROGRESS")
        assert device_under_test.obsState == ObsState.RESOURCING

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

        # still need to sleep. Wait for 2 polling periods
        time.sleep(0.2)
        assert device_under_test.ring_buffer_utilisation >= 0.0
        assert device_under_test.ring_buffer_size > 0
        assert device_under_test.number_subbands > 0
        assert device_under_test.ring_buffer_read >= 0
        assert device_under_test.ring_buffer_written >= 0

        for i in range(device_under_test.number_subbands):
            assert device_under_test.subband_ring_buffer_utilisations[i] >= 0.0
            assert device_under_test.subband_ring_buffer_sizes[i] > 0
            assert device_under_test.subband_ring_buffer_read[i] >= 0
            assert device_under_test.subband_ring_buffer_written[i] >= 0

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

    def test_simulation_mode(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        pst_lmc_service: TestPstLmcService,
        mock_servicer_context: MagicMock,
    ) -> None:
        """Test state model of PstSmrb."""
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

    def test_simulation_mode_when_not_in_empty_obs_state(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        assign_resources_request: dict,
    ) -> None:
        """Test state model of PstSmrb."""
        device_under_test.simulationMode = SimulationMode.TRUE
        assert device_under_test.simulationMode == SimulationMode.TRUE

        device_under_test.adminMode = AdminMode.ONLINE
        device_under_test.On()
        time.sleep(0.1)
        assert device_under_test.state() == DevState.ON

        resources = json.dumps(assign_resources_request)
        device_under_test.AssignResources(resources)
        time.sleep(0.5)
        assert device_under_test.obsState == ObsState.IDLE

        with pytest.raises(tango.DevFailed) as exc_info:
            device_under_test.simulationMode = SimulationMode.FALSE

        assert device_under_test.simulationMode == SimulationMode.TRUE
        exc_info.value.args[
            0
        ].desc == "ValueError: Unable to change simulation mode unless in EMPTY observation state"

    def test_simulation_mode_when_in_empty_obs_state(
        self: TestPstSmrb,
        device_under_test: DeviceProxy,
        pst_lmc_service: TestPstLmcService,
        mock_servicer_context: MagicMock,
    ) -> None:
        """Test state model of PstSmrb."""
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
