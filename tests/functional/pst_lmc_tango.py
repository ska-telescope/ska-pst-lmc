# -*- coding: utf-8 -*-
#
# This file is part of the SKA Low MCCS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

import time
from typing import List, Optional

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DeviceProxy, DevState
from tango.test_utils import MultiDeviceTestContext

from ska_pst_lmc.beam import PstBeam
from ska_pst_lmc.receive import PstReceive
from ska_pst_lmc.smrb import PstSmrb

pytestmark = pytest.mark.skip("all tests still WIP")

@scenario("features/pst_lmc_tango.feature", "BEAM turns on SMRB")
def test_beam_turns_on_smrb():
    pass


@scenario("features/pst_lmc_tango.feature", "BEAM turns on RECV")
def test_beam_turns_on_recv():
    pass


@scenario("features/pst_lmc_tango.feature", "BEAM assigns resources in SMRB")
def test_beam_assigns_resources_in_smrb():
    pass


@scenario("features/pst_lmc_tango.feature", "BEAM assigns resources in RECV")
def test_beam_assigns_resources_in_recv():
    pass


@pytest.fixture()
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


@pytest.fixture()
def devices_info() -> List[dict]:
    """Get device configuration for tests."""
    return [
        {
            "class": PstReceive,
            "devices": [
                {
                    "name": "test/recv/1",
                    "properties": {},
                }
            ],
        },
        {
            "class": PstSmrb,
            "devices": [
                {
                    "name": "test/smrb/1",
                    "properties": {},
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


device_fqdn_mapping = {
    "BEAM": "test/beam/1",
    "SMRB": "test/smrb/1",
    "RECV": "test/recv/1",
}


@pytest.fixture
def device_proxy(device: str, multidevice_test_context: MultiDeviceTestContext) -> DeviceProxy:
    return multidevice_test_context.get_device(device_fqdn_mapping[device])


@given(parsers.parse("{device} is running"))
def device_is_running(
    device_proxy: DeviceProxy,
):
    assert device_proxy is not None


@given(parsers.parse("{device} is ready to receive {command} command"))
def device_is_ready_to_receive_command(
    device_proxy: DeviceProxy,
    command: str,
):
    if command == "On":
        if device_proxy.adminMode != AdminMode.ONLINE:
            device_proxy.adminMode = AdminMode.ONLINE
            time.sleep(0.1)

        device_state = device_proxy.state()

        if device_state == DevState.ON:
            # need to turn device off
            device_proxy.Off()
            time.sleep(0.1)
        else:
            assert device_state in [
                DevState.OFF,
                DevState.STANDBY,
                DevState.ON,
                DevState.UNKNOWN,
            ]


@given(parsers.parse("{device} is in {state} observation state"))
def device_is_in_observation_state(
    device_proxy: DeviceProxy,
    state: str,
):
    if device_proxy.adminMode != AdminMode.ONLINE:
        device_proxy.adminMode = AdminMode.ONLINE
        time.sleep(0.1)

    if state == "EMPTY":
        # need some assertions before hand
        device_proxy.On()
        time.sleep(0.1)
        assert device_proxy.obsState == ObsState.EMPTY


@pytest.fixture
def command_params(command: str) -> Optional[str]:
    if command == "AssignResources":
        import json

        return json.dumps({"foo": "bar"})


@when(parsers.parse("{device} receives {command} command"))
def device_receives_command(device_proxy: DeviceProxy, command: str, command_params: Optional[str]):
    cmd = getattr(device_proxy, command)
    if command_params:
        cmd(command_params)
    else:
        cmd()

    if command == "On":
        time.sleep(0.1)


@then(parsers.parse("{device} is put into {state} admin state"))
def device_is_put_into_admin_state(
    device_proxy: DeviceProxy,
    state: str,
):
    expected_state = AdminMode[state.upper()]

    assert device_proxy.adminMode == expected_state


@then(parsers.parse("{device} is put into {state} observation state"))
def device_is_put_into_observation_state(
    device_proxy: DeviceProxy,
    state: str,
):
    expected_state = ObsState[state.upper()]

    assert device_proxy.obsState == expected_state


@then(parsers.parse("{device} is put into {first_state} then {second_state} observation state"))
def device_transitions_through_state_to_final_observation_state(
    device_proxy: DeviceProxy,
    first_state: str,
    second_state: str,
):
    expected_state = ObsState[first_state.upper()]
    assert device_proxy.obsState == expected_state

    time.sleep(0.5)

    expected_state = ObsState[second_state.upper()]
    assert device_proxy.obsState == expected_state
