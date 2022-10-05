# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the DSP API."""

from __future__ import annotations

import logging
import threading
import time
import unittest
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.dsp.dsp_process_api import PstDspProcessApiSimulator
from ska_pst_lmc.dsp.dsp_simulator import PstDspSimulator
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


@pytest.fixture
def simulation_api(
    simulator: PstDspSimulator,
    logger: logging.Logger,
    component_state_callback: MagicMock,
    background_task_processor: BackgroundTaskProcessor,
) -> PstDspProcessApiSimulator:
    """Create an instance of the Simluator API."""
    api = PstDspProcessApiSimulator(
        simulator=simulator, logger=logger, component_state_callback=component_state_callback
    )
    api._background_task_processor = background_task_processor

    return api


@pytest.fixture
def simulator() -> PstDspSimulator:
    """Create instance of a simulator to be used within the API."""
    return PstDspSimulator()


def test_dsp_simulator_api_monitor_calls_callback(
    simulation_api: PstDspProcessApiSimulator,
    subband_monitor_data_callback: MagicMock,
    abort_event: threading.Event,
    logger: logging.Logger,
) -> None:
    """Test simulatued monitoring calls subband_monitor_data_callback."""
    simulation_api._scanning = True

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


def test_dsp_simulator_api_assign_resources(
    simulation_api: PstDspProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that assign resources simulator calls task."""
    resources: dict = {}

    simulation_api.assign_resources(resources, task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=42),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=True)


def test_dsp_simulator_api_release_resources(
    simulation_api: PstDspProcessApiSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release resources simulator calls task."""
    simulation_api.release_resources(task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=48),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(resourced=False)


def test_dsp_simulator_api_configure(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
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
        call(progress=35),
        call(progress=81),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=True)


def test_dsp_simulator_api_deconfigure(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    with unittest.mock.patch.object(simulator, "deconfigure", wraps=simulator.deconfigure) as deconfigure:
        simulation_api.deconfigure(task_callback)
        deconfigure.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=22),
        call(progress=56),
        call(progress=76),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False)


def test_dsp_simulator_api_scan(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
    scan_request: dict,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that release_all simulator calls task."""
    with unittest.mock.patch.object(simulator, "scan", wraps=simulator.scan) as scan:
        simulation_api.scan(scan_request, task_callback)
        scan.assert_called_with(scan_request)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=59),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=True)


def test_dsp_simulator_api_end_scan(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that end_scan simulator calls task."""
    with unittest.mock.patch.object(simulator, "end_scan", wraps=simulator.end_scan) as end_scan:
        simulation_api.end_scan(task_callback)
        end_scan.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=31),
        call(progress=77),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_dsp_simulator_api_abort(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that abort simulator calls task."""
    with unittest.mock.patch.object(simulator, "abort", wraps=simulator.abort) as abort:
        simulation_api.abort(task_callback)
        abort.assert_called_once()

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=64),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(scanning=False)


def test_dsp_simulator_api_reset(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that reset simulator calls task."""
    simulation_api.reset(task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=37),
        call(progress=63),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False)


def test_dsp_simulator_api_restart(
    simulation_api: PstDspProcessApiSimulator,
    simulator: PstDspSimulator,
    component_state_callback: MagicMock,
    task_callback: MagicMock,
) -> None:
    """Test that restart simulator calls task."""
    simulation_api.restart(task_callback)

    expected_calls = [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=47),
        call(progress=87),
        call(status=TaskStatus.COMPLETED, result="Completed"),
    ]
    task_callback.assert_has_calls(expected_calls)
    component_state_callback.assert_called_with(configured=False, resourced=False)


def test_dsp_simulator_api_go_to_fault(
    simulation_api: PstDspProcessApiSimulator,
    component_state_callback: MagicMock,
) -> None:
    """Test that go_to_fault for simulator."""
    simulation_api.go_to_fault()
    component_state_callback.assert_called_once_with(obsfault=True)


def test_dsp_simulator_api_go_to_fault_if_scanning(
    simulation_api: PstDspProcessApiSimulator,
    component_state_callback: MagicMock,
) -> None:
    """Test that go_to_fault for simulator."""
    simulation_api._scanning = True

    simulation_api.go_to_fault()
    component_state_callback.assert_called_once_with(obsfault=True)

    assert not simulation_api._scanning, "Expected scanning to stop"


def test_dsp_simulator_api_go_to_fault_if_monitoring_event_is_not_set(
    simulation_api: PstDspProcessApiSimulator,
    component_state_callback: MagicMock,
) -> None:
    """Test that go_to_fault for simulator."""
    simulation_api._monitor_abort_event = threading.Event()

    simulation_api.go_to_fault()
    component_state_callback.assert_called_once_with(obsfault=True)

    assert simulation_api._monitor_abort_event.is_set(), "Expected the monitoring event to be set"
