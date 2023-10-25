# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains tests for the STAT component manager class."""

import logging
from typing import Any, Callable, Dict, cast
from unittest.mock import ANY, MagicMock, call

import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_tango_base.control_model import (
    CommunicationStatus,
    HealthState,
    LoggingLevel,
    PowerState,
    SimulationMode,
)
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import MonitorDataHandler, PstApiDeviceInterface
from ska_pst_lmc.stat.stat_component_manager import PstStatComponentManager
from ska_pst_lmc.stat.stat_model import StatMonitorData
from ska_pst_lmc.stat.stat_process_api import (
    PstStatProcessApi,
    PstStatProcessApiGrpc,
    PstStatProcessApiSimulator,
)
from ska_pst_lmc.stat.stat_util import calculate_stat_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService
from ska_pst_lmc.util import Callback
from ska_pst_lmc.util.validation import ValidationError


@pytest.fixture
def component_manager(
    device_interface: MagicMock,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstStatProcessApi,
    monkeypatch: pytest.MonkeyPatch,
) -> PstStatComponentManager:
    """Create instance of a component manager."""

    def submit_task(self: PstStatComponentManager, task: Callable, task_callback: Callback) -> None:
        task(task_callback=task_callback)

    monkeypatch.setattr(PstStatComponentManager, "submit_task", submit_task)

    return PstStatComponentManager(
        device_interface=cast(PstApiDeviceInterface[StatMonitorData], device_interface),
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
) -> PstStatProcessApi:
    """Create an API instance."""
    if simulation_mode == SimulationMode.TRUE:
        return PstStatProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
    else:
        return PstStatProcessApiGrpc(
            client_id=device_name,
            grpc_endpoint=grpc_endpoint,
            logger=logger,
            component_state_callback=component_state_callback,
        )


@pytest.fixture
def monitor_data(
    scan_request: Dict[str, Any],
) -> StatMonitorData:
    """Create an an instance of StatMonitorData for monitor data."""
    from ska_pst_lmc.stat.stat_simulator import PstStatSimulator

    simulator = PstStatSimulator()
    simulator.start_scan(args=scan_request)

    return simulator.get_data()


@pytest.fixture
def calculated_stat_subband_resources(beam_id: int, configure_beam_request: Dict[str, Any]) -> dict:
    """Fixture to calculate expected stat subband resources."""
    resources = calculate_stat_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
    )
    return resources[1]


def test_stat_cm_start_communicating_calls_connect_on_api(
    component_manager: PstStatComponentManager,
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
        ("real_pol_a_mean_freq_avg"),
        ("real_pol_a_variance_freq_avg"),
        ("real_pol_a_num_clipped_samples"),
        ("imag_pol_a_mean_freq_avg"),
        ("imag_pol_a_variance_freq_avg"),
        ("imag_pol_a_num_clipped_samples"),
        ("real_pol_a_mean_freq_avg_rfi_excised"),
        ("real_pol_a_variance_freq_avg_rfi_excised"),
        ("real_pol_a_num_clipped_samples_rfi_excised"),
        ("imag_pol_a_mean_freq_avg_rfi_excised"),
        ("imag_pol_a_variance_freq_avg_rfi_excised"),
        ("imag_pol_a_num_clipped_samples_rfi_excised"),
        ("real_pol_b_mean_freq_avg"),
        ("real_pol_b_variance_freq_avg"),
        ("real_pol_b_num_clipped_samples"),
        ("imag_pol_b_mean_freq_avg"),
        ("imag_pol_b_variance_freq_avg"),
        ("imag_pol_b_num_clipped_samples"),
        ("real_pol_b_mean_freq_avg_rfi_excised"),
        ("real_pol_b_variance_freq_avg_rfi_excised"),
        ("real_pol_b_num_clipped_samples_rfi_excised"),
        ("imag_pol_b_mean_freq_avg_rfi_excised"),
        ("imag_pol_b_variance_freq_avg_rfi_excised"),
        ("imag_pol_b_num_clipped_samples_rfi_excised"),
    ],
)
def test_stat_cm_properties_come_from_simulator_api_monitor_data(
    component_manager: PstStatComponentManager,
    monitor_data: StatMonitorData,
    property: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test properties are coming from API monitor data."""
    monkeypatch.setattr(MonitorDataHandler, "monitor_data", monitor_data)

    actual = getattr(component_manager, property)
    expected = getattr(monitor_data, property)

    assert actual == expected


def test_stat_cm_api_instance_changes_depending_on_simulation_mode(
    component_manager: PstStatComponentManager,
) -> None:
    """Test to assert that the process API changes depending on simulation mode."""
    assert component_manager.simulation_mode == SimulationMode.TRUE
    assert type(component_manager._api) == PstStatProcessApiSimulator

    component_manager.simulation_mode = SimulationMode.FALSE

    assert type(component_manager._api) == PstStatProcessApiGrpc


@pytest.mark.parametrize(
    "simulation_mode",
    [
        (SimulationMode.TRUE,),
        (SimulationMode.FALSE,),
    ],
)
def test_stat_cm_no_change_in_simulation_mode_value_wont_change_communication_state(
    device_name: str,
    component_manager: PstStatComponentManager,
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


def test_stat_cm_if_communicating_switching_simulation_mode_must_stop_then_restart(
    device_name: str,
    component_manager: PstStatComponentManager,
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


def test_stat_cm_not_communicating_switching_simulation_mode_not_try_to_establish_connection(
    component_manager: PstStatComponentManager,
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


def test_stat_cm_validate_configure_scan(
    component_manager: PstStatComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
    calculated_stat_subband_resources: dict,
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

    api.validate_configure_beam.assert_called_once_with(configuration=calculated_stat_subband_resources)
    api.validate_configure_scan.assert_called_once_with(configuration=configure_scan_request)

    calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)


def test_stat_cm_validate_configure_scan_fails_beam_configuration(
    component_manager: PstStatComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
    calculated_stat_subband_resources: dict,
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

    api.validate_configure_beam.assert_called_once_with(configuration=calculated_stat_subband_resources)
    api.validate_configure_scan.assert_not_called()

    calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, exception=validation_exception),
    ]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)


def test_stat_cm_validate_configure_scan_fails_scan_configuration(
    component_manager: PstStatComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
    calculated_stat_subband_resources: dict,
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

    api.validate_configure_beam.assert_called_once_with(configuration=calculated_stat_subband_resources)
    api.validate_configure_scan.assert_called_once_with(configuration=configure_scan_request)

    calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.FAILED, exception=validation_exception),
    ]
    cast(MagicMock, task_callback).assert_has_calls(calls=calls)


def test_stat_cm_configure_beam(
    component_manager: PstStatComponentManager,
    configure_beam_request: Dict[str, Any],
    task_callback: Callable,
    calculated_stat_subband_resources: dict,
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
        configuration=calculated_stat_subband_resources, task_callback=task_callback
    )


def test_stat_cm_deconfigure_beam(
    component_manager: PstStatComponentManager,
    task_callback: Callable,
) -> None:
    """Test that deconfigure beam calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.deconfigure_beam(task_callback=task_callback)

    api.deconfigure_beam.assert_called_once_with(task_callback=task_callback)


def test_stat_cm_configure_scan(
    component_manager: PstStatComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API for configure scan."""
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


def test_stat_cm_deconfigure_scan(
    component_manager: PstStatComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API for deconfigure scan."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.deconfigure_scan(task_callback=task_callback)

    api.deconfigure_scan.assert_called_once_with(
        task_callback=task_callback,
    )


def test_stat_cm_scan(
    component_manager: PstStatComponentManager,
    scan_request: Dict[str, Any],
    task_callback: Callable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the component manager calls the API to start scan."""
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


def test_stat_cm_stop_scan(
    component_manager: PstStatComponentManager,
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
    assert component_manager._monitor_data == StatMonitorData()
    monitor_data_callback.assert_called_once_with(StatMonitorData())


def test_stat_cm_abort(
    component_manager: PstStatComponentManager,
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


def test_stat_cm_obsreset(
    component_manager: PstStatComponentManager,
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


def test_stat_cm_go_to_fault(
    component_manager: PstStatComponentManager,
    device_interface: MagicMock,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API on go to fault."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.go_to_fault(task_callback=task_callback, fault_msg="sending STAT to fault")

    api.go_to_fault.assert_called_once()
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    cast(MagicMock, task_callback).assert_has_calls(calls)
    device_interface.handle_fault.assert_called_once_with(fault_msg="sending STAT to fault")


def test_stat_cm_on(
    component_manager: PstStatComponentManager,
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


def test_stat_cm_on_fails_if_not_communicating(
    component_manager: PstStatComponentManager,
) -> None:
    """Test that the component manager rejects a call to on if not communicating."""
    with pytest.raises(ConnectionError):
        component_manager.on()


def test_stat_cm_off(
    component_manager: PstStatComponentManager,
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


def test_stat_cm_off_fails_if_not_communicating(
    component_manager: PstStatComponentManager,
) -> None:
    """Test that the component manager rejects a call to 'off' if not communicating."""
    with pytest.raises(ConnectionError):
        component_manager.off()


def test_stat_cm_start_communicating(
    component_manager: PstStatComponentManager,
    device_interface: PstApiDeviceInterface,
) -> None:
    """Test STAT component manager when start_communicating is called."""
    component_manager._communication_state = CommunicationStatus.DISABLED
    component_manager.start_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(health_state=HealthState.OK)
    assert component_manager._communication_state == CommunicationStatus.ESTABLISHED


def test_stat_cm_stop_communicating(
    component_manager: PstStatComponentManager,
    device_interface: PstApiDeviceInterface,
) -> None:
    """Test STAT component manager when stop_communicating is called."""
    component_manager._communication_state = CommunicationStatus.ESTABLISHED
    component_manager.stop_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(
        health_state=HealthState.UNKNOWN
    )
    assert component_manager._communication_state == CommunicationStatus.DISABLED


@pytest.mark.parametrize(
    "log_level",
    [
        LoggingLevel.INFO,
        LoggingLevel.DEBUG,
        LoggingLevel.FATAL,
        LoggingLevel.WARNING,
        LoggingLevel.OFF,
    ],
)
def test_stat_cm_set_logging_level(
    component_manager: PstStatComponentManager,
    log_level: LoggingLevel,
) -> None:
    """Test STAT component manager when set_log_level is updated."""
    api = MagicMock()
    component_manager._api = api

    component_manager.set_logging_level(log_level=log_level)
    api.set_log_level.assert_called_once_with(log_level=log_level)
