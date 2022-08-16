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
from typing import Any, Callable
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc import PstReceiveSimulator
from ska_pst_lmc.receive.receive_process_api import PstReceiveProcessApiSimulator
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


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


def test_simulated_monitor_calls_callback(
    simulation_api: PstReceiveProcessApiSimulator,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""

    def _abort_monitor() -> None:
        logger.debug("Test sleeping 600ms")
        time.sleep(0.6)
        logger.debug("Aborting monitoring.")
        abort_event.set()

    abort_thread = threading.Thread(target=_abort_monitor, daemon=True)
    abort_thread.start()

    simulation_api.monitor(
        subband_monitor_data_callback=subband_monitor_data_callback,
        polling_rate=500,
        monitor_abort_event=abort_event,
    )
    abort_thread.join()
    logger.debug("Abort thread finished.")

    calls = [
        call(subband_id=subband_id, subband_data=subband_data)
        for (subband_id, subband_data) in simulation_api._simulator.get_subband_data().items()
    ]
    subband_monitor_data_callback.assert_has_calls(calls=calls)


def test_assign_resources(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that assign resources simulator calls task."""
    resources: dict = {}

    simulation_api.assign_resources(resources, task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=33),
        call(progress=66),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=True)


def test_release_resources(
    simulation_api: PstReceiveProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    simulation_api.release_resources(task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=50),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=False)


def test_configure(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
    configure_scan_request: dict,
) -> None:
    """Test that release_all simulator calls task."""
    with unittest.mock.patch.object(simulator, "configure", wraps=simulator.configure) as configure:
        simulation_api.configure(configure_scan_request, task_callback)
        configure.assert_called_with(configuration=configure_scan_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=30),
        call(progress=60),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=True)


def test_deconfigure(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    with unittest.mock.patch.object(simulator, "deconfigure", wraps=simulator.deconfigure) as deconfigure:
        simulation_api.deconfigure(task_callback)
        deconfigure.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=31),
        call(progress=89),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False)


def test_scan(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    args = {"foo": "bar"}
    with unittest.mock.patch.object(simulator, "scan", wraps=simulator.scan) as scan:
        simulation_api.scan(args, task_callback)
        scan.assert_called_with(args)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=27),
        call(progress=69),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=True)


def test_end_scan(
    simulation_api: PstReceiveProcessApiSimulator,
    simulator: PstReceiveSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that end_scan simulator calls task."""
    with unittest.mock.patch.object(simulator, "end_scan", wraps=simulator.end_scan) as end_scan:
        simulation_api.end_scan(task_callback)
        end_scan.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=32),
        call(progress=88),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_abort(
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
