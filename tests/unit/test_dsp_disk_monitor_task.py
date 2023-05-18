# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Test to the DSP disk monitor task."""

from __future__ import annotations

import logging
import threading
import time
from typing import Generator
from unittest.mock import MagicMock

import pytest

from ska_pst_lmc.dsp.disk_monitor_task import DiskMonitorTask, MonitoringState


@pytest.fixture
def mock_stats_action() -> MagicMock:
    """Get a mock stats api for testing."""
    return MagicMock()


@pytest.fixture
def disk_monitor(
    mock_stats_action: MagicMock,
    logger: logging.Logger,
    monitoring_polling_rate: int,
) -> Generator[DiskMonitorTask, None, None]:
    """Create a disk monitor task as a fixture."""
    disk_monitor = DiskMonitorTask(
        stats_action=mock_stats_action,
        monitoring_polling_rate=monitoring_polling_rate,
        logger=logger,
    )

    yield disk_monitor

    disk_monitor.shutdown()


def test_disk_monitor(
    disk_monitor: DiskMonitorTask,
    mock_stats_action: MagicMock,
    monitoring_polling_rate: int,
) -> None:
    """Test happy path of disk monitor."""
    disk_monitor.start_monitoring()
    assert disk_monitor._state == MonitoringState.MONITORING

    # this should have multiple polling periods
    time.sleep(2.5 * monitoring_polling_rate / 1000.0)

    disk_monitor.stop_monitoring()
    assert disk_monitor._state == MonitoringState.STOPPED

    mock_stats_action.assert_called()
    assert mock_stats_action.call_count > 1


def test_disk_monitor_monitoring_stops_when_api_throws_exception(
    disk_monitor: DiskMonitorTask,
    mock_stats_action: MagicMock,
    monitoring_polling_rate: int,
) -> None:
    """Test that monitoring stops if there is an error from the API."""
    mock_stats_action.side_effect = RuntimeError("oops something went wrong")

    disk_monitor.start_monitoring()
    time.sleep(1.5 * monitoring_polling_rate / 1000.0)

    assert disk_monitor._state == MonitoringState.STOPPED


def test_disk_monitor_if_already_stopping(disk_monitor: DiskMonitorTask) -> None:
    """Test that monitoring can start even if there currently stopping."""
    disk_monitor._state = MonitoringState.STOPPING

    def _action() -> None:
        time.sleep(0.2)
        disk_monitor._set_state(MonitoringState.STOPPED)

    t = threading.Thread(target=_action)
    t.start()

    disk_monitor.start_monitoring()
    t.join()
    assert disk_monitor._state == MonitoringState.MONITORING


def test_disk_monitor_if_already_monitoring(
    disk_monitor: DiskMonitorTask,
    mock_stats_action: MagicMock,
    monitoring_polling_rate: int,
) -> None:
    """Test if alreading in a monitoring state that new background process not starts to monitor."""
    disk_monitor._state = MonitoringState.MONITORING

    disk_monitor.start_monitoring()
    time.sleep(1.5 * monitoring_polling_rate / 1000.0)
    mock_stats_action.assert_not_called()


def test_disk_monitor_start_monitoring_throws_except_if_already_shutdown(
    disk_monitor: DiskMonitorTask,
) -> None:
    """Test that start monitoring will throw an exception if task is shutdown."""
    disk_monitor._state = MonitoringState.SHUTDOWN

    with pytest.raises(RuntimeError) as exc_info:
        disk_monitor.start_monitoring()

    assert str(exc_info.value) == "Monitoring task has already been shutdown.  Can't restart."


def test_disk_monitor_stop_monitoring_when_in_waiting_state(disk_monitor: DiskMonitorTask) -> None:
    """Test stop_monitoring if already in a WAITING state."""
    disk_monitor._state = MonitoringState.WAITING

    disk_monitor.stop_monitoring()

    assert disk_monitor._state == MonitoringState.WAITING


def test_disk_monitor_stop_monitoring_when_in_stopped_state(disk_monitor: DiskMonitorTask) -> None:
    """Test stop_monitoring if already in a STOPPED state."""
    disk_monitor._state = MonitoringState.STOPPED

    disk_monitor.stop_monitoring()

    assert disk_monitor._state == MonitoringState.STOPPED


def test_disk_monitor_stop_monitoring_when_in_stopping_state(disk_monitor: DiskMonitorTask) -> None:
    """Test stop_monitoring if already in a STOPPING state.

    This needs to a background thread to update the state to STOPPED.
    """
    disk_monitor._state = MonitoringState.STOPPING

    def _action() -> None:
        time.sleep(0.5)
        disk_monitor._set_state(MonitoringState.STOPPED)

    t = threading.Thread(target=_action)
    t.start()
    disk_monitor.stop_monitoring(timeout=1.0)
    t.join()

    assert disk_monitor._state == MonitoringState.STOPPED


def test_disk_monitor_shutdown(disk_monitor: DiskMonitorTask) -> None:
    """Test shutdown when monitoring."""
    disk_monitor.start_monitoring()
    assert disk_monitor._state == MonitoringState.MONITORING
    time.sleep(0.1)

    disk_monitor.shutdown()
    assert disk_monitor._state == MonitoringState.SHUTDOWN
