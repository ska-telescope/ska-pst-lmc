# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the SMRB component managers class."""

import logging
from typing import Any, Callable, Dict, cast
from unittest.mock import ANY, MagicMock, call

import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_tango_base.control_model import CommunicationStatus, HealthState, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import MonitorDataHandler, PstApiDeviceInterface
from ska_pst_lmc.smrb.smrb_component_manager import PstSmrbComponentManager
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData
from ska_pst_lmc.smrb.smrb_process_api import (
    PstSmrbProcessApi,
    PstSmrbProcessApiGrpc,
    PstSmrbProcessApiSimulator,
)
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService
from ska_pst_lmc.util import Callback
from ska_pst_lmc.util.validation import ValidationError


@pytest.fixture
def component_manager(
    device_interface: MagicMock,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstSmrbProcessApi,
    monkeypatch: pytest.MonkeyPatch,
) -> PstSmrbComponentManager:
    """Create instance of a component manager."""

    def submit_task(self: PstSmrbComponentManager, task: Callable, task_callback: Callback) -> None:
        task(task_callback=task_callback)

    monkeypatch.setattr(PstSmrbComponentManager, "submit_task", submit_task)

    return PstSmrbComponentManager(
        device_interface=cast(PstApiDeviceInterface[SmrbMonitorData], device_interface),
        simulation_mode=simulation_mode,
        logger=logger,
        api=api,
    )


@pytest.fixture
def api(
    device_name: str,
    grpc_endpoint: str,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    component_state_callback: Callable,
) -> PstSmrbProcessApi:
    """Create an API instance."""
    if simulation_mode == SimulationMode.TRUE:
        return PstSmrbProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
    else:
        return PstSmrbProcessApiGrpc(
            client_id=device_name,
            grpc_endpoint=grpc_endpoint,
            logger=logger,
            component_state_callback=component_state_callback,
        )


@pytest.fixture
def monitor_data(
    scan_request: Dict[str, Any],
) -> SmrbMonitorData:
    """Create an an instance of ReceiveData for monitor data."""
    from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator

    simulator = PstSmrbSimulator()
    simulator.start_scan(args=scan_request)

    return simulator.get_data()


@pytest.fixture
def calculated_smrb_subband_resources(beam_id: int, configure_beam_request: Dict[str, Any]) -> dict:
    """Fixture to calculate expected smrb subband resources."""
    resources = calculate_smrb_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
    )
    return resources[1]


def test_smrb_cm_start_communicating_calls_connect_on_api(
    component_manager: PstSmrbComponentManager,
) -> None:
    """Assert start/stop communicating calls API."""
    api = MagicMock()
    component_manager._api = api

    component_manager.start_communicating()
    api.connect.assert_called_once()
    api.disconnect.assert_not_called()

    component_manager.stop_communicating()
    api.disconnect.assert_called_once()


@pytest.mark.parametrize(
    "property",
    [
        ("ring_buffer_utilisation"),
        ("ring_buffer_size"),
        ("number_subbands"),
        ("ring_buffer_read"),
        ("ring_buffer_written"),
        ("subband_ring_buffer_utilisations"),
        ("subband_ring_buffer_sizes"),
        ("subband_ring_buffer_read"),
        ("subband_ring_buffer_written"),
    ],
)
def test_smrb_cm_properties_come_from_simulator_api_monitor_data(
    component_manager: PstSmrbComponentManager,
    monitor_data: SmrbMonitorData,
    property: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test properties are coming from API monitor data."""
    monkeypatch.setattr(MonitorDataHandler, "monitor_data", monitor_data)

    actual = getattr(component_manager, property)
    expected = getattr(monitor_data, property)

    assert actual == expected


def test_smrb_cm_api_instance_changes_depending_on_simulation_mode(
    component_manager: PstSmrbComponentManager,
) -> None:
    """Test to assert that the process API changes depending on simulation mode."""
    assert component_manager.simulation_mode == SimulationMode.TRUE
    assert type(component_manager._api) == PstSmrbProcessApiSimulator

    component_manager.simulation_mode = SimulationMode.FALSE

    assert type(component_manager._api) == PstSmrbProcessApiGrpc


@pytest.mark.parametrize(
    "simulation_mode",
    [
        (SimulationMode.TRUE,),
        (SimulationMode.FALSE,),
    ],
)
def test_smrb_cm_no_change_in_simulation_mode_value_wont_change_communication_state(
    device_name: str,
    component_manager: PstSmrbComponentManager,
    simulation_mode: SimulationMode,
    pst_lmc_service: TestPstLmcService,
    mock_servicer_context: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test no change in simulation mode does not change communication state."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    monkeypatch.setattr(component_manager, "_update_communication_state", update_communication_state)

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == simulation_mode

    component_manager.start_communicating()
    assert component_manager.communication_state == CommunicationStatus.ESTABLISHED
    if simulation_mode == SimulationMode.FALSE:
        mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=device_name))

    calls = [call(CommunicationStatus.NOT_ESTABLISHED), call(CommunicationStatus.ESTABLISHED)]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = simulation_mode
    update_communication_state.assert_not_called()


def test_smrb_cm_if_communicating_switching_simulation_mode_must_stop_then_restart(
    device_name: str,
    component_manager: PstSmrbComponentManager,
    pst_lmc_service: TestPstLmcService,
    mock_servicer_context: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test if communicating and simulation mode changes, then need to reconnect."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    monkeypatch.setattr(component_manager, "_update_communication_state", update_communication_state)

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == SimulationMode.TRUE

    component_manager.start_communicating()
    assert component_manager.communication_state == CommunicationStatus.ESTABLISHED

    calls = [call(CommunicationStatus.NOT_ESTABLISHED), call(CommunicationStatus.ESTABLISHED)]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.FALSE
    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=device_name))

    calls = [
        call(CommunicationStatus.DISABLED),
        call(CommunicationStatus.NOT_ESTABLISHED),
        call(CommunicationStatus.ESTABLISHED),
    ]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.TRUE
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()


def test_smrb_cm_not_communicating_switching_simulation_mode_not_try_to_establish_connection(
    component_manager: PstSmrbComponentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test if not communicating and change of simulation happens, don't do anything."""
    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    monkeypatch.setattr(component_manager, "_update_communication_state", update_communication_state)

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == SimulationMode.TRUE

    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.FALSE
    update_communication_state.assert_not_called()
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.TRUE
    update_communication_state.assert_not_called()


def test_smrb_cm_validate_configure_scan(
    component_manager: PstSmrbComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
    calculated_smrb_subband_resources: dict,
) -> None:
    """Test that validate configuration when valid."""
    api = MagicMock()
    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.validate_configure_scan(
        configuration=configure_scan_request, task_callback=task_callback
    )

    api.validate_configure_beam.assert_called_once_with(configuration=calculated_smrb_subband_resources)
    api.validate_configure_scan.assert_called_once_with(configuration=configure_scan_request)

    calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=50),
        call(status=TaskStatus.COMPLETED),
    ]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)


def test_smrb_cm_validate_configure_scan_fails_beam_configuration(
    component_manager: PstSmrbComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
    calculated_smrb_subband_resources: dict,
) -> None:
    """Test that validate configuration when invalid beam configuration."""
    api = MagicMock()
    validation_exception = ValidationError("This is not the configuration you're looking for.")
    api.validate_configure_beam.side_effect = validation_exception

    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.validate_configure_scan(
        configuration=configure_scan_request, task_callback=task_callback
    )

    api.validate_configure_beam.assert_called_once_with(configuration=calculated_smrb_subband_resources)
    api.validate_configure_scan.assert_not_called()

    calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, exception=validation_exception),
    ]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)


def test_smrb_cm_validate_configure_scan_fails_scan_configuration(
    component_manager: PstSmrbComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
    calculated_smrb_subband_resources: dict,
) -> None:
    """Test that validate configuration when invalid scan configuration."""
    api = MagicMock()
    validation_exception = ValidationError("That's no scan configuration")
    api.validate_configure_scan.side_effect = validation_exception

    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.validate_configure_scan(
        configuration=configure_scan_request, task_callback=task_callback
    )

    api.validate_configure_beam.assert_called_once_with(configuration=calculated_smrb_subband_resources)
    api.validate_configure_scan.assert_called_once_with(configuration=configure_scan_request)

    calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=50),
        call(status=TaskStatus.FAILED, exception=validation_exception),
    ]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)


def test_smrb_cm_configure_beam(
    component_manager: PstSmrbComponentManager,
    configure_beam_request: Dict[str, Any],
    task_callback: Callable,
    calculated_smrb_subband_resources: dict,
) -> None:
    """Test that configure beam calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.configure_beam(configuration=configure_beam_request, task_callback=task_callback)

    api.configure_beam.assert_called_once_with(
        configuration=calculated_smrb_subband_resources, task_callback=task_callback
    )


def test_smrb_cm_deconfigure_beam(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that configure beam calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.deconfigure_beam(task_callback=task_callback)

    api.deconfigure_beam.assert_called_once_with(task_callback=task_callback)


def test_smrb_cm_configure_scan(
    component_manager: PstSmrbComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API for configure."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.configure_scan(configuration=configure_scan_request, task_callback=task_callback)

    api.configure_scan.assert_called_once_with(
        configuration=configure_scan_request,
        task_callback=task_callback,
    )


def test_smrb_cm_deconfigure_scan(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API for configure."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.deconfigure_scan(task_callback=task_callback)

    api.deconfigure_scan.assert_called_once_with(
        task_callback=task_callback,
    )


def test_smrb_cm_scan(
    component_manager: PstSmrbComponentManager,
    scan_request: Dict[str, Any],
    task_callback: Callable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the component manager calls the API start a scan."""
    api = MagicMock()
    component_manager._api = api

    def _submit_background_task(task: Callable, task_callback: Callable) -> None:
        task(task_callback=task_callback)

    monkeypatch.setattr(component_manager, "_submit_background_task", _submit_background_task)

    component_manager.start_scan(scan_request, task_callback=task_callback)

    api.start_scan.assert_called_once_with(
        args=scan_request,
        task_callback=task_callback,
    )
    api.monitor.assert_called_once_with(
        subband_monitor_data_callback=component_manager._monitor_data_handler.handle_subband_data,
        polling_rate=component_manager.monitoring_polling_rate,
    )


def test_smrb_cm_stop_scan(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
    monitor_data_callback: MagicMock,
) -> None:
    """Test that the component manager calls the API to end scan."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.stop_scan(task_callback=task_callback)

    api.stop_scan.assert_called_once_with(
        task_callback=task_callback,
    )
    assert component_manager._monitor_data == SmrbMonitorData()
    monitor_data_callback.assert_called_once_with(SmrbMonitorData())


def test_smrb_cm_abort(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API to abort on service."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.abort(task_callback=task_callback)

    api.abort.assert_called_once_with(
        task_callback=task_callback,
    )


def test_smrb_cm_obsreset(
    component_manager: PstSmrbComponentManager,
    device_interface: MagicMock,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API to reset service in ABORTED or FAULT state."""

    def _side_effect(*args: Any, task_callback: Callable, **kwargs: Any) -> None:
        task_callback(configured=False, resourced=False)
        task_callback(status=TaskStatus.COMPLETED, result="Completed")

    api = MagicMock()
    api.reset.side_effect = _side_effect
    component_manager._api = api

    component_manager.obsreset(task_callback=task_callback)

    api.reset.assert_called_once_with(
        task_callback=ANY,
    )

    calls = [call(configured=False, resourced=False), call(status=TaskStatus.COMPLETED, result="Completed")]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)
    device_interface.update_health_state.assert_called_once_with(health_state=HealthState.OK)


def test_smrb_cm_go_to_fault(
    component_manager: PstSmrbComponentManager,
    device_interface: MagicMock,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API start a scan."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.go_to_fault(task_callback=task_callback, fault_msg="sending SMRB to fault")

    api.go_to_fault.assert_called_once()
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    cast(MagicMock, task_callback).assert_has_calls(calls)
    device_interface.handle_fault.assert_called_once_with(fault_msg="sending SMRB to fault")


def test_smrb_cm_on(
    component_manager: PstSmrbComponentManager,
    device_interface: MagicMock,
) -> None:
    """Test that the component manager handles the call to on."""
    task_callback = MagicMock()

    # enforce the communication state to be establised.
    component_manager._communication_state = CommunicationStatus.ESTABLISHED

    component_manager.on(task_callback=task_callback)
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)

    device_interface.handle_component_state_change.assert_called_once_with(power=PowerState.ON)
    device_interface.update_health_state.assert_not_called()


def test_smrb_cm_on_fails_if_not_communicating(
    component_manager: PstSmrbComponentManager,
) -> None:
    """Test that the component manager rejects a call to on if not communicating."""
    with pytest.raises(ConnectionError):
        component_manager.on()


def test_smrb_cm_off(
    component_manager: PstSmrbComponentManager,
    device_interface: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the component manager handles the call to 'off'."""
    task_callback = MagicMock()

    # enforce the communication state to be establised.
    component_manager._communication_state = CommunicationStatus.ESTABLISHED

    component_manager.off(task_callback=task_callback)
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)

    device_interface.handle_component_state_change.assert_called_once_with(power=PowerState.OFF)
    device_interface.update_health_state.assert_not_called()


def test_smrb_cm_off_fails_if_not_communicating(
    component_manager: PstSmrbComponentManager,
) -> None:
    """Test that the component manager rejects a call to 'off' if not communicating."""
    with pytest.raises(ConnectionError):
        component_manager.off()


def test_smrb_cm_start_communicating(
    component_manager: PstSmrbComponentManager,
    device_interface: PstApiDeviceInterface,
) -> None:
    """Test RECV component manager when start_communicating is called."""
    component_manager._communication_state = CommunicationStatus.DISABLED
    component_manager.start_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(health_state=HealthState.OK)
    assert component_manager._communication_state == CommunicationStatus.ESTABLISHED


def test_smrb_cm_stop_communicating(
    component_manager: PstSmrbComponentManager,
    device_interface: PstApiDeviceInterface,
) -> None:
    """Test RECV component manager when stop_communicating is called."""
    component_manager._communication_state = CommunicationStatus.ESTABLISHED
    component_manager.stop_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(
        health_state=HealthState.UNKNOWN
    )
    assert component_manager._communication_state == CommunicationStatus.DISABLED
