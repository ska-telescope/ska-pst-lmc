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
from typing import Any, Dict

import backoff
import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DevState

from ska_pst_lmc import DeviceProxyFactory
from tests.conftest import TangoDeviceCommandChecker


@pytest.mark.integration
class TestPstBeam:
    """Test class used for testing the PstReceive TANGO device."""

    @pytest.mark.forked
    def test_configure_then_scan_then_stop(
        self: TestPstBeam,
        configure_beam_request: Dict[str, Any],
        configure_scan_request: Dict[str, Any],
        scan_request: Dict[str, Any],
        tango_device_command_checker: TangoDeviceCommandChecker,
        logger: logging.Logger,
    ) -> None:
        """Test state model of PstReceive."""
        dsp_proxy = DeviceProxyFactory.get_device("low-pst/dsp/01")
        recv_proxy = DeviceProxyFactory.get_device("low-pst/recv/01")
        smrb_proxy = DeviceProxyFactory.get_device("low-pst/smrb/01")
        beam_proxy = DeviceProxyFactory.get_device("low-pst/beam/01")

        # tango_change_event_helper = TangoChangeEventHelper(
        #     device_under_test=beam_proxy.device,
        #     change_event_callbacks=change_event_callbacks,
        #     logger=logger,
        # )
        # tango_device_command_checker = TangoDeviceCommandChecker(
        #     tango_change_event_helper=tango_change_event_helper,
        #     logger=logger,
        # )

        def assert_state(state: DevState) -> None:
            assert beam_proxy.state() == state
            assert recv_proxy.state() == state
            assert smrb_proxy.state() == state
            assert dsp_proxy.state() == state

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
            assert dsp_proxy.obsState == obsState

        # better handle of setup and teardown
        assert_state(DevState.DISABLE)

        beam_proxy.adminMode = AdminMode.ONLINE
        time.sleep(0.2)
        assert recv_proxy.adminMode == AdminMode.ONLINE
        assert smrb_proxy.adminMode == AdminMode.ONLINE
        assert dsp_proxy.adminMode == AdminMode.ONLINE

        assert_state(DevState.OFF)

        try:
            tango_device_command_checker.assert_command(
                lambda: beam_proxy.On(), expected_obs_state_events=[ObsState.EMPTY]
            )
            assert_state(DevState.ON)

            # need to configure beam
            assert_obstate(ObsState.EMPTY)

            resources = json.dumps(configure_beam_request)
            tango_device_command_checker.assert_command(
                lambda: beam_proxy.AssignResources(resources),
                expected_obs_state_events=[
                    ObsState.RESOURCING,
                    ObsState.IDLE,
                ],
            )
            assert_obstate(ObsState.IDLE)

            configuration = json.dumps(configure_scan_request)
            tango_device_command_checker.assert_command(
                lambda: beam_proxy.Configure(configuration),
                expected_obs_state_events=[
                    ObsState.CONFIGURING,
                    ObsState.READY,
                ],
            )
            assert_obstate(ObsState.READY)

            scan = str(scan_request)
            tango_device_command_checker.assert_command(
                lambda: beam_proxy.Scan(scan),
                expected_obs_state_events=[
                    ObsState.SCANNING,
                ],
            )
            assert_obstate(ObsState.SCANNING)

            tango_device_command_checker.assert_command(
                lambda: beam_proxy.EndScan(),
                expected_obs_state_events=[
                    ObsState.READY,
                ],
            )

            logger.info("Device is now in ready state.")

            tango_device_command_checker.assert_command(
                lambda: beam_proxy.Off(),
            )
            assert_state(DevState.OFF)
        finally:
            beam_proxy.Off()
            time.sleep(1)
            beam_proxy.adminMode = AdminMode.OFFLINE
            time.sleep(0.1)
            assert recv_proxy.adminMode == AdminMode.OFFLINE
            assert smrb_proxy.adminMode == AdminMode.OFFLINE
            assert dsp_proxy.adminMode == AdminMode.OFFLINE

            assert_state(DevState.DISABLE)
