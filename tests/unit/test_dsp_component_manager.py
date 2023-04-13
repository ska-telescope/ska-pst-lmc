# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the DSP component managers class."""

import logging
from typing import Any, Callable, Dict, Optional, cast
from unittest.mock import ANY, MagicMock, call

import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_tango_base.control_model import CommunicationStatus, HealthState, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import MonitorDataHandler, PstApiDeviceInterface
from ska_pst_lmc.dsp.dsp_component_manager import PstDspComponentManager
from ska_pst_lmc.dsp.dsp_model import DspDiskMonitorData
from ska_pst_lmc.dsp.dsp_process_api import PstDspProcessApi, PstDspProcessApiGrpc, PstDspProcessApiSimulator
from ska_pst_lmc.dsp.dsp_util import calculate_dsp_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService
from ska_pst_lmc.util.callback import Callback


@pytest.fixture
def component_manager(
    device_interface: MagicMock,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstDspProcessApi,
    monkeypatch: pytest.MonkeyPatch,
) -> PstDspComponentManager:
    """Create instance of a component manager."""
    # override the background processing.
    def submit_task(
        self: PstDspComponentManager,
        task: Callable,
        *args: Any,
        task_callback: Optional[Callable] = None,
        **kwargs: Any
    ) -> None:
        task(*args, task_callback=task_callback, **kwargs)

    monkeypatch.setattr(PstDspComponentManager, "submit_task", submit_task)

    return PstDspComponentManager(
        device_interface=cast(PstApiDeviceInterface[DspDiskMonitorData], device_interface),
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
) -> PstDspProcessApi:
    """Create an API instance."""
    if simulation_mode == SimulationMode.TRUE:
        return PstDspProcessApiSimulator(
            logger=logger,
            component_state_callback=component_state_callback,
        )
    else:
        return PstDspProcessApiGrpc(
            client_id=device_name,
            grpc_endpoint=grpc_endpoint,
            logger=logger,
            component_state_callback=component_state_callback,
        )


@pytest.fixture
def monitor_data(
    scan_request: Dict[str, Any],
) -> DspDiskMonitorData:
    """Create an an instance of DspDiskMonitorData for monitor data."""
    from ska_pst_lmc.dsp.dsp_simulator import PstDspSimulator

    simulator = PstDspSimulator()
    simulator.start_scan(args=scan_request)

    return simulator.get_data()


@pytest.fixture
def calculated_dsp_subband_resources(beam_id: int, configure_beam_request: Dict[str, Any]) -> dict:
    """Fixture to calculate expected dsp subband resources."""
    resources = calculate_dsp_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
    )
    return resources[1]


def test_dsp_cm_start_communicating_calls_connect_on_api(
    component_manager: PstDspComponentManager,
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
        ("disk_capacity"),
        ("available_disk_space"),
        ("disk_used_bytes"),
        ("disk_used_percentage"),
        ("data_recorded"),
        ("data_record_rate"),
        ("available_recording_time"),
        ("subband_data_recorded"),
        ("subband_data_record_rate"),
    ],
)
def test_dsp_cm_properties_come_from_simulator_api_monitor_data(
    component_manager: PstDspComponentManager,
    monitor_data: DspDiskMonitorData,
    property: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test properties are coming from API monitor data."""
    monkeypatch.setattr(MonitorDataHandler, "monitor_data", monitor_data)

    actual = getattr(component_manager, property)
    expected = getattr(monitor_data, property)

    assert actual == expected


def test_dsp_cm_api_instance_changes_depending_on_simulation_mode(
    component_manager: PstDspComponentManager,
) -> None:
    """Test to assert that the process API changes depending on simulation mode."""
    assert component_manager.simulation_mode == SimulationMode.TRUE
    assert type(component_manager._api) == PstDspProcessApiSimulator

    component_manager.simulation_mode = SimulationMode.FALSE

    assert type(component_manager._api) == PstDspProcessApiGrpc


@pytest.mark.parametrize(
    "simulation_mode",
    [
        (SimulationMode.TRUE,),
        (SimulationMode.FALSE,),
    ],
)
def test_dsp_cm_no_change_in_simulation_mode_value_wont_change_communication_state(
    device_name: str,
    component_manager: PstDspComponentManager,
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


def test_dsp_cm_if_communicating_switching_simulation_mode_must_stop_then_restart(
    device_name: str,
    component_manager: PstDspComponentManager,
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


def test_dsp_cm_not_communicating_switching_simulation_mode_not_try_to_establish_connection(
    component_manager: PstDspComponentManager,
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


def test_dsp_cm_configure_beam(
    component_manager: PstDspComponentManager,
    configure_beam_request: Dict[str, Any],
    task_callback: Callable,
    calculated_dsp_subband_resources: dict,
    api: PstDspProcessApi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that configure beam calls the API correctly."""
    configure_beam = MagicMock()
    monkeypatch.setattr(api, "configure_beam", configure_beam)

    component_manager.configure_beam(resources=configure_beam_request, task_callback=task_callback)

    configure_beam.assert_called_once_with(
        resources=calculated_dsp_subband_resources, task_callback=task_callback
    )


def test_dsp_cm_deconfigure_beam(
    component_manager: PstDspComponentManager,
    task_callback: Callable,
) -> None:
    """Test that configure beam calls the API correctly."""
    api = MagicMock()
    component_manager._api = api

    component_manager.deconfigure_beam(task_callback=task_callback)

    api.deconfigure_beam.assert_called_once_with(task_callback=task_callback)


def test_dsp_cm_configure_scan(
    component_manager: PstDspComponentManager,
    configure_scan_request: Dict[str, Any],
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API for configure."""
    api = MagicMock()
    component_manager._api = api

    component_manager.configure_scan(configuration=configure_scan_request, task_callback=task_callback)

    api.configure_scan.assert_called_once_with(
        configuration=configure_scan_request,
        task_callback=task_callback,
    )


def test_dsp_cm_deconfigure_scan(
    component_manager: PstDspComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API for configure."""
    api = MagicMock()
    component_manager._api = api

    component_manager.deconfigure_scan(task_callback=task_callback)

    api.deconfigure_scan.assert_called_once_with(
        task_callback=task_callback,
    )


def test_dsp_cm_scan(
    component_manager: PstDspComponentManager,
    scan_request: Dict[str, Any],
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API start a scan."""
    api = MagicMock()
    component_manager._api = api

    component_manager.start_scan(scan_request, task_callback=task_callback)

    api.start_scan.assert_called_once_with(
        args=scan_request,
        task_callback=task_callback,
    )
    api.monitor.assert_called_once_with(
        subband_monitor_data_callback=component_manager._monitor_data_handler.handle_subband_data,
        polling_rate=component_manager._monitor_polling_rate,
    )


def test_dsp_cm_stop_scan(
    component_manager: PstDspComponentManager,
    task_callback: Callable,
    monitor_data_callback: MagicMock,
) -> None:
    """Test that the component manager calls the API to end scan."""
    api = MagicMock()
    component_manager._api = api

    component_manager.stop_scan(task_callback=task_callback)

    api.stop_scan.assert_called_once_with(
        task_callback=task_callback,
    )
    assert component_manager._monitor_data == DspDiskMonitorData()
    monitor_data_callback.assert_called_once_with(DspDiskMonitorData())


def test_dsp_cm_abort(
    component_manager: PstDspComponentManager,
    task_callback: Callback,
) -> None:
    """Test that the component manager calls the API to abort on service."""
    api = MagicMock()
    component_manager._api = api

    component_manager.abort(task_callback=task_callback)

    api.abort.assert_called_once_with(
        task_callback=task_callback,
    )


def test_dsp_cm_obsreset(
    component_manager: PstDspComponentManager,
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


def test_dsp_cm_go_to_fault(
    component_manager: PstDspComponentManager,
    device_interface: MagicMock,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API start a scan."""
    api = MagicMock()
    component_manager._api = api

    component_manager.go_to_fault(task_callback=task_callback, fault_msg="putting DSP into fault")

    api.go_to_fault.assert_called_once()
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    cast(MagicMock, task_callback).assert_has_calls(calls)
    device_interface.handle_fault.assert_called_once_with(fault_msg="putting DSP into fault")


def test_dsp_cm_on(
    component_manager: PstDspComponentManager,
    device_interface: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the component manager handles the call to 'on'."""
    task_callback = MagicMock()

    # stub _get_disk_stats_from_api
    _get_disk_stats_from_api = MagicMock()
    monkeypatch.setattr(component_manager, "_get_disk_stats_from_api", _get_disk_stats_from_api)

    # enforce the communication state to be establised.
    component_manager._communication_state = CommunicationStatus.ESTABLISHED

    component_manager.on(task_callback=task_callback)
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)

    device_interface.handle_component_state_change.assert_called_once_with(power=PowerState.ON)
    device_interface.update_health_state.assert_not_called()
    _get_disk_stats_from_api.assert_called_once()


def test_dsp_cm_on_fails_if_not_communicating(
    component_manager: PstDspComponentManager,
) -> None:
    """Test that the component manager rejects a call to 'on' if not communicating."""
    with pytest.raises(ConnectionError):
        component_manager.on()


def test_dsp_cm_off(
    component_manager: PstDspComponentManager,
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


def test_dsp_cm_off_fails_if_not_communicating(
    component_manager: PstDspComponentManager,
) -> None:
    """Test that the component manager rejects a call to 'off' if not communicating."""
    with pytest.raises(ConnectionError):
        component_manager.off()


def test_dsp_cm_start_communicating(
    component_manager: PstDspComponentManager,
    device_interface: PstApiDeviceInterface,
) -> None:
    """Test DSP component manager when start_communicating is called."""
    component_manager._communication_state = CommunicationStatus.DISABLED
    component_manager.start_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(health_state=HealthState.OK)
    assert component_manager._communication_state == CommunicationStatus.ESTABLISHED


def test_dsp_cm_stop_communicating(
    component_manager: PstDspComponentManager,
    device_interface: PstApiDeviceInterface,
) -> None:
    """Test DSP component manager when stop_communicating is called."""
    component_manager._communication_state = CommunicationStatus.ESTABLISHED
    component_manager.stop_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(
        health_state=HealthState.UNKNOWN
    )
    assert component_manager._communication_state == CommunicationStatus.DISABLED
