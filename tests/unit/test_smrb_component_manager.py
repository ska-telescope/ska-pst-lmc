# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the SMRB component managers class."""

import logging
import time
from typing import Callable, cast
from unittest.mock import MagicMock, call

import pytest
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import ConnectionRequest, ConnectionResponse
from ska_tango_base.control_model import CommunicationStatus, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component import MonitorDataHandler
from ska_pst_lmc.smrb.smrb_component_manager import PstSmrbComponentManager
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData
from ska_pst_lmc.smrb.smrb_process_api import (
    PstSmrbProcessApi,
    PstSmrbProcessApiGrpc,
    PstSmrbProcessApiSimulator,
)
from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources
from ska_pst_lmc.test.test_grpc_server import TestPstLmcService


@pytest.fixture
def component_manager(
    device_name: str,
    grpc_endpoint: str,
    simulation_mode: SimulationMode,
    logger: logging.Logger,
    api: PstSmrbProcessApi,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    monitor_data_callback: Callable,
) -> PstSmrbComponentManager:
    """Create instance of a component manager."""
    return PstSmrbComponentManager(
        device_name=device_name,
        process_api_endpoint=grpc_endpoint,
        simulation_mode=simulation_mode,
        logger=logger,
        communication_state_callback=communication_state_callback,
        component_state_callback=component_state_callback,
        api=api,
        monitor_data_callback=monitor_data_callback,
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
    scan_request: dict,
) -> SmrbMonitorData:
    """Create an an instance of ReceiveData for monitor data."""
    from ska_pst_lmc.smrb.smrb_simulator import PstSmrbSimulator

    simulator = PstSmrbSimulator()
    simulator.start_scan(args=scan_request)

    return simulator.get_data()


@pytest.fixture
def calculated_smrb_subband_resources(beam_id: int, configure_beam_request: dict) -> dict:
    """Fixture to calculate expected smrb subband resources."""
    resources = calculate_smrb_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
    )
    return resources[1]


def test_smrb_cm_start_communicating_calls_connect_on_api(
    component_manager: PstSmrbComponentManager,
    api: PstSmrbProcessApi,
) -> None:
    """Assert start/stop communicating calls API."""
    api = MagicMock(wraps=api)
    component_manager._api = api

    component_manager.start_communicating()
    time.sleep(0.1)
    api.connect.assert_called_once()
    api.disconnect.assert_not_called()

    component_manager.stop_communicating()
    time.sleep(0.1)
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
) -> None:
    """Test no change in simulation mode does not change communication state."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    component_manager._update_communication_state = update_communication_state

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == simulation_mode

    component_manager.start_communicating()
    time.sleep(0.1)
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
) -> None:
    """Test if communicating and simulation mode changes, then need to reconnect."""
    response = ConnectionResponse()
    mock_servicer_context.connect = MagicMock(return_value=response)

    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    component_manager._update_communication_state = update_communication_state

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == SimulationMode.TRUE

    component_manager.start_communicating()
    time.sleep(0.1)
    assert component_manager.communication_state == CommunicationStatus.ESTABLISHED

    calls = [call(CommunicationStatus.NOT_ESTABLISHED), call(CommunicationStatus.ESTABLISHED)]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.FALSE
    time.sleep(0.1)
    mock_servicer_context.connect.assert_called_once_with(ConnectionRequest(client_id=device_name))

    calls = [
        call(CommunicationStatus.DISABLED),
        call(CommunicationStatus.NOT_ESTABLISHED),
        call(CommunicationStatus.ESTABLISHED),
    ]
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.TRUE
    time.sleep(0.1)
    update_communication_state.assert_has_calls(calls)
    update_communication_state.reset_mock()


def test_smrb_cm_not_communicating_switching_simulation_mode_not_try_to_establish_connection(
    component_manager: PstSmrbComponentManager,
) -> None:
    """Test if not communicating and change of simulation happens, don't do anything."""
    update_communication_state = MagicMock(wraps=component_manager._update_communication_state)
    component_manager._update_communication_state = update_communication_state

    assert component_manager.communication_state == CommunicationStatus.DISABLED
    assert component_manager.simulation_mode == SimulationMode.TRUE

    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.FALSE
    update_communication_state.assert_not_called()
    update_communication_state.reset_mock()

    component_manager.simulation_mode = SimulationMode.TRUE
    update_communication_state.assert_not_called()


def test_smrb_cm_smrb_configure_beam(
    component_manager: PstSmrbComponentManager,
    configure_beam_request: dict,
    task_callback: Callable,
    calculated_smrb_subband_resources: dict,
) -> None:
    """Test that assign resources calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    # override the background processing.
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.assign(resources=configure_beam_request, task_callback=task_callback)

    api.configure_beam.assert_called_once_with(
        resources=calculated_smrb_subband_resources, task_callback=task_callback
    )


def test_smrb_cm_smrb_deconfigure_beam(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that assign resources calls the API correctly."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback
    )

    component_manager.release_all(task_callback=task_callback)

    api.deconfigure_beam.assert_called_once_with(task_callback=task_callback)


def test_smrb_cm_configure_scan(
    component_manager: PstSmrbComponentManager,
    configure_scan_request: dict,
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


def test_smrb_cm_smrb_scan(
    component_manager: PstSmrbComponentManager,
    scan_request: dict,
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
        scan_request,
        task_callback=task_callback,
    )
    api.monitor.assert_called_once_with(
        subband_monitor_data_callback=component_manager._monitor_data_handler.handle_subband_data,
        polling_rate=component_manager._monitor_polling_rate,
    )


def test_smrb_cm_smrb_stop_scan(
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


def test_smrb_cm_smrb_abort(
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


def test_smrb_cm_smrb_obsreset(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API to reset service in ABORTED or FAULT state."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.obsreset(task_callback=task_callback)

    api.reset.assert_called_once_with(
        task_callback=task_callback,
    )


def test_smrb_cm_smrb_restart(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API to restart service in ABORTED or FAULT state."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.restart(task_callback=task_callback)

    api.restart.assert_called_once_with(
        task_callback=task_callback,
    )


def test_smrb_cm_recv_go_to_fault(
    component_manager: PstSmrbComponentManager,
    task_callback: Callable,
) -> None:
    """Test that the component manager calls the API start a scan."""
    api = MagicMock()
    component_manager._api = api
    component_manager._submit_background_task = lambda task, task_callback: task(  # type: ignore
        task_callback=task_callback,
    )

    component_manager.go_to_fault(task_callback=task_callback)

    api.go_to_fault.assert_called_once()
    calls = [call(status=TaskStatus.IN_PROGRESS), call(status=TaskStatus.COMPLETED, result="Completed")]
    cast(MagicMock, task_callback).assert_has_calls(calls)
