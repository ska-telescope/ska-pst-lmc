# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Test to the RECV Tango device for PST.LMC."""

from __future__ import annotations

import time
from typing import Generator

import pytest
from ska_tango_base.control_model import AdminMode, ControlMode, HealthState, SimulationMode, TestMode
from tango import DevFailed, DeviceProxy, DevState
from tango.test_context import DeviceTestContext

from ska_pst_lmc import PstReceive
from ska_pst_lmc.receive import generate_random_update
from ska_pst_lmc.receive.receive_model import ReceiveData


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


class TestPstReceive:
    @pytest.fixture(scope="class")
    def device_test_config(self, device_properties):
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
            # "component_manager_patch": lambda self: PstReceiveComponentManager(
            #     SimulationMode.TRUE,
            #     self.logger,
            #     self._communication_state_changed,
            #     self._component_state_changed,
            # ),
            # "component_manager_patch": lambda self: ReferenceBaseComponentManager(
            #     self.logger,
            #     self._communication_state_changed,
            #     self._component_state_changed,
            # ),
            "properties": device_properties,
            "memorized": {"adminMode": str(AdminMode.ONLINE.value)},
        }

    def test_State(self, device_under_test: DeviceProxy):
        """
        Test for State.

        :param device_under_test: a proxy to the device under test
        """
        assert device_under_test.state() == DevState.OFF
        assert device_under_test.Status() == "The device is in OFF state."

    def test_GetVersionInfo(self, device_under_test):
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
        print(version_info)
        assert len(version_info) == 1
        assert re.match(version_pattern, version_info[0])

    def test_Reset(self, device_under_test):
        """
        Test for Reset.

        :param device_under_test: a proxy to the device under test
        """
        # PROTECTED REGION ID(SKABaseDevice.test_Reset) ENABLED START #
        # The main test of this command is
        # TestSKABaseDevice_commands::test_ResetCommand
        assert device_under_test.state() == DevState.OFF

        with pytest.raises(
            DevFailed,
            match="Command Reset not allowed when the device is in OFF state",
        ):
            _ = device_under_test.Reset()

    def test_online(self, device_under_test) -> None:
        device_under_test.adminMode = AdminMode.ONLINE
        time.sleep(0.1)

        assert device_under_test.adminMode == AdminMode.ONLINE
        assert device_under_test.state() == DevState.ON
        assert device_under_test.status() == "The device is in ON state."
        assert device_under_test.healthState == HealthState.OK
        assert device_under_test.controlMode == ControlMode.REMOTE
        assert device_under_test.simulationMode == SimulationMode.TRUE
        assert device_under_test.testMode == TestMode.TEST

    # def test_On(self, device_under_test, tango_change_event_helper):
    #     """
    #     Test for On command.

    #     :param device_under_test: a proxy to the device under test
    #     :param tango_change_event_helper: helper fixture that simplifies
    #         subscription to the device under test with a callback.
    #     """
    #     assert device_under_test.state() == DevState.OFF

    #     device_state_callback = tango_change_event_helper.subscribe("state")
    #     device_state_callback.assert_next_change_event(DevState.OFF)

    #     device_status_callback = tango_change_event_helper.subscribe("status")
    #     device_status_callback.assert_next_change_event("The device is in OFF state.")

    #     command_progress_callback = tango_change_event_helper.subscribe(
    #         "longRunningCommandProgress"
    #     )
    #     command_progress_callback.assert_next_change_event(None)

    #     command_status_callback = tango_change_event_helper.subscribe(
    #         "longRunningCommandStatus"
    #     )
    #     command_status_callback.assert_next_change_event(None)

    #     command_result_callback = tango_change_event_helper.subscribe(
    #         "longRunningCommandResult"
    #     )
    #     command_result_callback.assert_next_change_event(("", ""))

    #     [[result_code], [command_id]] = device_under_test.On()
    #     assert result_code == ResultCode.QUEUED
    #     command_status_callback.assert_next_change_event((command_id, "QUEUED"))
    #     command_status_callback.assert_next_change_event((command_id, "IN_PROGRESS"))

    #     command_progress_callback.assert_next_change_event((command_id, "33"))
    #     command_progress_callback.assert_next_change_event((command_id, "66"))

    #     command_status_callback.assert_next_change_event((command_id, "COMPLETED"))

    #     device_state_callback.assert_next_change_event(DevState.ON)
    #     device_status_callback.assert_next_change_event("The device is in ON state.")
    #     assert device_under_test.state() == DevState.ON

    #     command_result_callback.assert_next_change_event(
    #         (command_id, json.dumps([int(ResultCode.OK), "On command completed OK"]))
    #     )

    #     # Check what happens if we call On() when the device is already ON.
    #     [[result_code], [message]] = device_under_test.On()
    #     assert result_code == ResultCode.REJECTED
    #     assert message == "Device is already in ON state."

    #     command_status_callback.assert_not_called()
    #     command_progress_callback.assert_not_called()
    #     command_result_callback.assert_not_called()

    #     device_state_callback.assert_not_called()
    #     device_status_callback.assert_not_called()

    # def test_InitDevice(
    #     self: TestPstReceive,
    #     device_under_test: DeviceProxy,
    # ) -> None:
    #     """
    #     Test for Initial state.

    #     :param device_under_test: fixture that provides a
    #         :py:class:`tango.DeviceProxy` to the device under test, in a
    #         :py:class:`tango.test_context.DeviceTestContext`.
    #     """
    #     assert device_under_test.state() == DevState.DISABLE
    #     assert device_under_test.status() == "The device is in DISABLE state."
    #     assert device_under_test.adminMode == AdminMode.OFFLINE
    #     assert device_under_test.healthState == HealthState.UNKNOWN
    #     assert device_under_test.controlMode == ControlMode.REMOTE
    #     assert device_under_test.simulationMode == SimulationMode.TRUE
    #     assert device_under_test.testMode == TestMode.TEST

    # def test_Status(self, device_under_test):
    #     """
    #     Test for Status.

    #     :param device_under_test: a proxy to the device under test
    #     """
    #     assert device_under_test.Status() == "The device is in ON state."

    # def test_recevie_device_gets_attributes_from_simulator(self,
    #     device_under_test: DeviceProxy,
    #     receive_data: ReceiveData,
    #     monkeypatch: pytest.monkeypatch,  # type: ignore[name-defined]
    # ) -> None:
    #     import numpy as np
    #     # need to mock the ReceiveSimulator's update data so we know what values it should be.
    #     def mock_get_data(*args: Any, **kwargs: Any) -> ReceiveData:
    #         return receive_data

    #     monkeypatch.setattr(PstReceiveSimulator, "get_data", mock_get_data)

    #     assert device_under_test.received_data == 0
    #     assert device_under_test.received_rate == 0.
    #     assert device_under_test.dropped_data == 0
    #     assert device_under_test.dropped_rate == 0.0
    #     assert device_under_test.misordered_packets == 0
    #     assert device_under_test.malformed_packets == 0
    #     assert device_under_test.relative_weight == 0.0

    #     device_under_test.adminMode = AdminMode.ONLINE
    #     time.sleep(0.1)

    #     assert device_under_test.state() == DevState.ON
    #     assert device_under_test.status() == "The device is in ON state."
    #     assert device_under_test.controlMode == ControlMode.REMOTE
    #     assert device_under_test.simulationMode == SimulationMode.TRUE
    # assert device_under_test.testMode == TestMode.TEST

    # device_under_test.Init()

    # assert device_under_test.received_data == receive_data.received_data
    # assert device_under_test.received_rate == receive_data.received_rate
    # assert device_under_test.dropped_data == receive_data.dropped_data
    # assert device_under_test.dropped_rate == receive_data.dropped_rate
    # assert device_under_test.misordered_packets == receive_data.misordeded_packets
    # assert device_under_test.malformed_packets == receive_data.malformed_packets
    # assert device_under_test.relative_weights == receive_data.relative_weights
    # assert device_under_test.relative_weight == receive_data.relative_weight


#         # assert receive_device.battery_voltage_a == pytest.approx(27.66106)
#         # assert receive_device.battery_current_a == pytest.approx(0.08056619)
#         # assert receive_device.battery_voltage_b == pytest.approx(28.1005)
#         # assert receive_device.battery_current_b == pytest.approx(3.08837)
#         # assert receive_device.hydrogen_pressure_setting == pytest.approx(5.8300632)
#         # assert receive_device.hydrogen_pressure_measured == pytest.approx(1.5319785)
#         # assert receive_device.purifier_current == pytest.approx(0.61889489)
#         # assert receive_device.dissociator_current == pytest.approx(0.5163561)
#         # assert receive_device.dissociator_light == pytest.approx(4.64842559)
#         # assert receive_device.internal_top_heater_voltage == pytest.approx(1.45995719)
#         # assert receive_device.internal_bottom_heater_voltage == pytest.approx(0.94238039)
#         # assert receive_device.internal_side_heater_voltage == pytest.approx(1.391598)
#         # assert receive_device.thermal_control_unit_heater_voltage == pytest.approx(2.5439388)
#         # assert receive_device.external_side_heater_voltage == pytest.approx(1.32812159)
#         # assert receive_device.external_bottom_heater_voltage == pytest.approx(1.1279268)
#         # assert receive_device.isolator_heater_voltage == pytest.approx(0.84472439)
#         # assert receive_device.tube_heater_voltage == pytest.approx(0.56640479)
#         # assert receive_device.boxes_temperature == pytest.approx(42.96864)
#         # assert receive_device.boxes_current == pytest.approx(0.26122979)
#         # assert receive_device.ambient_temperature == pytest.approx(22.607364)
#         # assert receive_device.cfield_voltage == pytest.approx(0.0463866)
#         # assert receive_device.varactor_diode_voltage == pytest.approx(3.61815479)
#         # assert receive_device.external_high_voltage_value == pytest.approx(3.50194416)
#         # assert receive_device.external_high_current_value == pytest.approx(16.11324)
#         # assert receive_device.internal_high_voltage_value == pytest.approx(3.50389728)
#         # assert receive_device.internal_high_current_value == pytest.approx(14.16012)
#         # assert receive_device.hydrogen_storage_pressure == pytest.approx(1.0937472)
#         # assert receive_device.hydrogen_storage_heater_voltage == pytest.approx(12.951627)
#         # assert receive_device.pirani_heater_voltage == pytest.approx(11.3586135)
#         # assert receive_device.oscillator_100mhz_voltage == pytest.approx(0.634764)
#         # assert receive_device.amplitude_405khz_voltage == pytest.approx(8.715798)
#         # assert receive_device.oscillator_voltage == pytest.approx(4.29198119)
#         # assert receive_device.positive24vdc == pytest.approx(24.90228)
#         # assert receive_device.positive15vdc == pytest.approx(15.78125)
#         # assert receive_device.negative15vdc == pytest.approx(-15.625)
#         # assert receive_device.positive5vdc == pytest.approx(5.15592)
#         # assert receive_device.negative5vdc == pytest.approx(0.0)
#         # assert receive_device.positive8vdc == pytest.approx(8.0072999)
#         # assert receive_device.positive18vdc == pytest.approx(0.0)
#         # assert receive_device.lock100mhz == pytest.approx(4.882499)
#         # assert receive_device.phase_lock_loop_lockstatus

#     # assert attributes are defaults
#     # need to set simulation mode
#     # need to set Admin mode
#     # assert attributes are not defaults


# # ensure component manager is created
# # putting the device into ONLINE mode will allow for the communication to start
# #   - this will then allow for checking if attributes change.
# #   -
