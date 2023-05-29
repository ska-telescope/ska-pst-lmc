# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV API."""

import logging
import threading
import time
import unittest
from typing import Any, Callable, Dict
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.commands import TaskStatus
from ska_tango_base.control_model import LoggingLevel

from ska_pst_lmc import PstReceiveSimulator
from ska_pst_lmc.receive.receive_process_api import PstReceiveProcessApiSimulator
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.validation import ValidationError


@pytest.fixture
def background_task_processor(
    logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> BackgroundTaskProcessor:
    """Create mock for background task processing."""

    def _submit_task(
        action_fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> MagicMock:
        action_fn()
        return MagicMock()

    # need to stub the submit_task and replace
    processor = BackgroundTaskProcessor(default_logger=logger)
    monkeypatch.setattr(processor, "submit_task", _submit_task)
    return processor


@pytest.fixture
def component_state_callback() -> Callable:
    """Create a mock component state callback to test actions."""
    return MagicMock()


@pytest.fixture
def task_callback() -> Callable:
    """Create a mock component to validate task callbacks."""
    return MagicMock()


@pytest.fixture
def simulation_api(
    simulator: PstReceiveSimulator,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    background_task_processor: BackgroundTaskProcessor,
) -> PstReceiveProcessApiSimulator:
    """Create an instance of the Simluator API."""
    api = PstReceiveProcessApiSimulator(
        simulator=simulator, logger=logger, component_state_callback=component_state_callback
    )
    api._background_task_processor = background_task_processor

    return api


@pytest.fixture
def simulator() -> PstReceiveSimulator:
    """Create instance of a simulator to be used within the API."""
    return PstReceiveSimulator()


def test_recv_simulator_api_simulated_monitor_calls_callback(
    simulation_api: PstReceiveProcessApiSimulator,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""
    simulation_api._scanning = True

    def _abort_monitor() -> None:
        time.sleep(0.015)
        logger.debug("Aborting monitoring.")
        abort_event.set()

    abort_thread = threading.Thread(target=_abort_monitor, daemon=True)
    abort_thread.start()

    simulation_api.monitor(
        subband_monitor_data_callback=subband_monitor_data_callback,
        polling_rate=10,
        monitor_abort_event=abort_event,
    )
    abort_thread.join()

    calls = [
        call(subband_id=subband_id, subband_data=subband_data)
        for (subband_id, subband_data) in simulation_api._simulator.get_subband_data().items()
    ]
    subband_monitor_data_callback.assert_has_calls(calls=calls)


def test_recv_simulator_api_validate_configure_beam(
    simulation_api: PstReceiveProcessApiSimulator,
) -> None:
    """Tests that validate configure beam on simulator API."""
    simulation_api.fail_validate_configure_beam = False
    simulation_api.validate_configure_beam(configuration={})


def test_recv_simulator_api_validate_configure_beam_throws_validation_exception(
    simulation_api: PstReceiveProcessApiSimulator,
) -> None:
    """Tests that validate configure beam on simulator API throws exception."""
    simulation_api.fail_validate_configure_beam = True
    with pytest.raises(ValidationError):
        simulation_api.validate_configure_beam(configuration={})


def test_recv_simulator_api_configure_beam(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that configure beam simulator calls task."""
    resources: dict = {}

    simulation_api.configure_beam(resources, task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=33),
        call(progress=66),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=True)


def test_recv_simulator_api_deconfigure_beam(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that deconfigure_beam simulator calls task."""
    simulation_api.deconfigure_beam(task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=50),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=False)


def test_recv_simulator_api_validate_configure_scan(
    simulation_api: PstReceiveProcessApiSimulator,
) -> None:
    """Tests that validate configure scan on simulator API."""
    simulation_api.fail_validate_configure_scan = False
    simulation_api.validate_configure_scan(configuration={})


def test_recv_simulator_api_validate_configure_scan_throws_validation_exception(
    simulation_api: PstReceiveProcessApiSimulator,
) -> None:
    """Tests that validate configure scan on simulator API throws validation exception."""
    simulation_api.fail_validate_configure_scan = True
    with pytest.raises(ValidationError):
        simulation_api.validate_configure_scan(configuration={})


def test_recv_simulator_api_configure_scan(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
    configure_scan_request: Dict[str, Any],
) -> None:
    """Test that configure_scan simulator calls task."""
    with unittest.mock.patch.object(
        simulator, "configure_scan", wraps=simulator.configure_scan
    ) as configure_scan:
        simulation_api.configure_scan(configure_scan_request, task_callback)
        configure_scan.assert_called_with(configuration=configure_scan_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=30),
        call(progress=60),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=True)


def test_recv_simulator_api_deconfigure_scan(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that deconfigure_scan simulator calls task."""
    with unittest.mock.patch.object(
        simulator, "deconfigure_scan", wraps=simulator.deconfigure_scan
    ) as deconfigure_scan:
        simulation_api.deconfigure_scan(task_callback)
        deconfigure_scan.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=31),
        call(progress=89),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False)


def test_recv_simulator_api_start_scan(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that start_scan simulator calls task."""
    args = {"foo": "bar"}
    with unittest.mock.patch.object(simulator, "start_scan", wraps=simulator.start_scan) as start_scan:
        simulation_api.start_scan(args, task_callback)
        start_scan.assert_called_with(args)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=27),
        call(progress=69),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=True)


def test_recv_simulator_api_stop_scan(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that stop_scan simulator calls task."""
    with unittest.mock.patch.object(simulator, "stop_scan", wraps=simulator.stop_scan) as stop_scan:
        simulation_api.stop_scan(task_callback)
        stop_scan.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=32),
        call(progress=88),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_recv_simulator_api_abort(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that abort simulator calls task."""
    with unittest.mock.patch.object(simulator, "abort", wraps=simulator.abort) as abort:
        simulation_api.abort(task_callback)
        abort.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=60),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_recv_simulator_api_reset(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that reset simulator calls task."""
    with unittest.mock.patch.object(simulator, "reset", wraps=simulator.reset) as reset:
        simulation_api.reset(task_callback)
        reset.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=47),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False, resourced=False)


def test_recv_simulator_api_go_to_fault(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
) -> None:
    """Test that go_to_fault for simulator."""
    simulation_api.go_to_fault()
    component_state_callback.assert_called_once_with(obsfault=True)


def test_recv_simulator_api_go_to_fault_if_scanning(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
) -> None:
    """Test that go_to_fault for simulator."""
    simulation_api._scanning = True

    simulation_api.go_to_fault()
    component_state_callback.assert_called_once_with(obsfault=True)

    assert not simulation_api._scanning, "Expected scanning to stop"


def test_recv_simulator_api_go_to_fault_if_monitoring_event_is_not_set(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
) -> None:
    """Test that go_to_fault for simulator."""
    simulation_api._monitor_abort_event = threading.Event()

    simulation_api.go_to_fault()
    component_state_callback.assert_called_once_with(obsfault=True)

    assert simulation_api._monitor_abort_event.is_set(), "Expected the monitoring event to be set"


def test_recv_simulator_api_get_env(
    simulation_api: PstReceiveProcessApiSimulator,
) -> None:
    """Test get_env returns expected values."""
    output = simulation_api.get_env()

    expected = {"data_host": "127.0.0.1", "data_port": 32080}

    assert output == expected


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
def test_recv_simulator_api_set_log_level(
    simulation_api: PstReceiveProcessApiSimulator, log_level: LoggingLevel
) -> None:
    """Test the set_log_level on simulator API."""
    simulation_api.set_log_level(log_level=log_level)
    assert simulation_api.logging_level == log_level
