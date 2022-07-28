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
from typing import Dict

import backoff
import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_base.executor import TaskStatus
from tango import DevState

from ska_pst_lmc import DeviceProxyFactory
from tests.conftest import ChangeEventDict, TangoChangeEventHelper


@pytest.mark.integration
class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.mark.forked
    def test_configure_then_scan_then_stop(
        self: TestPstBeam,
        assign_resources_request: dict,
        change_event_callbacks: ChangeEventDict,
        logger: logging.Logger,
    ) -> None:
        """Test state model of PstReceive."""
        recv_proxy = DeviceProxyFactory.get_device("test/receive/1")
        smrb_proxy = DeviceProxyFactory.get_device("test/smrb/1")
        beam_proxy = DeviceProxyFactory.get_device("test/beam/1")

        tango_change_event_helper = TangoChangeEventHelper(
            device_under_test=beam_proxy.device,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

        long_running_command_status_callback = tango_change_event_helper.subscribe("longRunningCommandStatus")

        @backoff.on_exception(
            backoff.expo,
            AssertionError,
            factor=1,
            max_time=5.0,
        )
        def assert_command_status(command_id: str, status: str) -> None:
            evt = long_running_command_status_callback.get_next_change_event()

            # need to covert to map
            evt_iter = iter(evt)
            evt_map: Dict[str, str] = {k: v for (k, v) in zip(evt_iter, evt_iter)}

            assert command_id in evt_map
            assert evt_map[command_id] == status

        def assert_state(state: DevState) -> None:
            assert beam_proxy.state() == state
            assert recv_proxy.state() == state
            assert smrb_proxy.state() == state

        @backoff.on_exception(
            backoff.expo,
            AssertionError,
            factor=1,
            max_time=5.0,
        )
        def assert_obstate(obsState: ObsState) -> None:
            assert beam_proxy.obsState == obsState
            assert recv_proxy.obsState == obsState
            assert smrb_proxy.obsState == obsState

        # better handle of setup and teardown
        assert_state(DevState.DISABLE)

        beam_proxy.adminMode = AdminMode.ONLINE
        time.sleep(0.2)
        assert recv_proxy.adminMode == AdminMode.ONLINE
        assert smrb_proxy.adminMode == AdminMode.ONLINE

        assert_state(DevState.OFF)

        try:
            [[result], [command_id]] = beam_proxy.On()
            assert result == TaskStatus.IN_PROGRESS

            assert_command_status(command_id, "QUEUED")
            assert_command_status(command_id, "IN_PROGRESS")
            assert_command_status(command_id, "COMPLETED")
            assert_state(DevState.ON)

            # need to assign resources
            assert_obstate(ObsState.EMPTY)

            resources = json.dumps(assign_resources_request)
            [[result], [command_id]] = beam_proxy.AssignResources(resources)

            assert result == TaskStatus.IN_PROGRESS

            assert_command_status(command_id, "QUEUED")
            assert_command_status(command_id, "IN_PROGRESS")
            assert beam_proxy.obsState == ObsState.RESOURCING

            assert_command_status(command_id, "COMPLETED")
            assert_obstate(ObsState.IDLE)

            configuration = json.dumps({"nchan": 1024})
            [[result], [command_id]] = beam_proxy.Configure(configuration)
            assert result == TaskStatus.IN_PROGRESS

            assert_command_status(command_id, "IN_PROGRESS")
            assert_command_status(command_id, "COMPLETED")
            assert_obstate(ObsState.READY)

            scan = json.dumps({"cat": "dog"})
            [[result], [command_id]] = beam_proxy.Scan(scan)
            assert result == TaskStatus.IN_PROGRESS

            assert_command_status(command_id, "QUEUED")
            assert_command_status(command_id, "IN_PROGRESS")
            assert_command_status(command_id, "COMPLETED")
            assert_obstate(ObsState.SCANNING)

            [[result], [command_id]] = beam_proxy.EndScan()
            assert result == TaskStatus.IN_PROGRESS

            assert_command_status(command_id, "QUEUED")
            assert_command_status(command_id, "IN_PROGRESS")
            assert_command_status(command_id, "COMPLETED")
            assert_obstate(ObsState.READY)

            logger.info("Device is now in ready state.")

            beam_proxy.Off()
            time.sleep(0.5)
            assert_state(DevState.OFF)
        finally:
            beam_proxy.Off()
            time.sleep(1)
            beam_proxy.adminMode = AdminMode.OFFLINE
            time.sleep(0.1)
            assert recv_proxy.adminMode == AdminMode.OFFLINE
            assert smrb_proxy.adminMode == AdminMode.OFFLINE

            assert_state(DevState.DISABLE)
