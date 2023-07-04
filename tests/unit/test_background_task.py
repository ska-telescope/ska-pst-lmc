# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains the pytest tests for the BackgroundTask class."""

import logging
import time
from threading import Thread
from typing import Callable, Optional
from unittest.mock import MagicMock

import pytest

from ska_pst_lmc.util.background_task import BackgroundTask


def test_new_task_is_in_stopped_state() -> None:
    """Assert that a new background task not in running state when created."""
    task: BackgroundTask = BackgroundTask(action_fn=lambda: None, logger=logging.getLogger())

    assert not task.running()


def test_run_creates_background_thread() -> None:
    """Assert background task creates a background thread when run."""
    task: BackgroundTask = BackgroundTask(action_fn=lambda: None, frequency=1.0, logger=logging.getLogger())
    assert task._thread is None

    task.run()

    assert task._thread is not None


def test_calling_run_on_running_task_does_nothing() -> None:
    """Assert calling run again on running task does not create new thread."""
    task: BackgroundTask = BackgroundTask(action_fn=lambda: None, frequency=1.0, logger=logging.getLogger())
    assert task._thread is None

    task.run()
    current_thread: Optional[Thread] = task._thread
    task.run()

    assert current_thread == task._thread


def test_calling_stop_on_running_task_stops_task() -> None:
    """Assert that calling stop on task cleans up task."""
    task: BackgroundTask = BackgroundTask(action_fn=lambda: None, frequency=1.0, logger=logging.getLogger())
    task.run()
    time.sleep(0.01)
    task.stop()

    assert task._thread is None
    assert task._completed


def test_calling_run_on_completed_task_throws_exception() -> None:
    """Assert that calling run a stopped task will raise an error."""
    task: BackgroundTask = BackgroundTask(action_fn=lambda: None, frequency=1.0, logger=logging.getLogger())
    task.run()
    time.sleep(0.01)
    task.stop()

    with pytest.raises(AssertionError) as e_info:
        task.run()

    assert "Task has already completed, cannot run it again." == str(e_info.value)


def test_assert_run_calls_action_fn_once() -> None:
    """Assert that callable is called only once when frequency is not set."""
    mock: MagicMock = MagicMock()
    action: Callable[[], None] = mock
    task: BackgroundTask = BackgroundTask(action_fn=action, logger=logging.getLogger())
    task.run()
    while task.running():
        time.sleep(0.05)
    mock.assert_called_once()
    assert task._thread is None
    assert task._completed


def test_assert_run_calls_action_fn_multiple_times() -> None:
    """Assert that callable is called multipled times if frequency set."""
    mock: MagicMock = MagicMock()
    action: Callable[[], None] = mock
    task: BackgroundTask = BackgroundTask(action_fn=action, frequency=1000.0, logger=logging.getLogger())
    task.run()
    time.sleep(0.01)
    task.stop()
    mock.assert_called()
    assert mock.call_count > 1


def test_assert_if_task_throws_exception() -> None:
    """Assert that background task handles exceptions being thrown by task."""
    err: ValueError = ValueError()

    def raise_err() -> None:
        raise err

    task: BackgroundTask = BackgroundTask(action_fn=raise_err, logger=logging.getLogger())
    assert task.exception() is None
    assert not task.has_errored()
    task.run()
    while task.running():
        time.sleep(0.05)
    assert not task.running()
    assert task.has_errored()
    assert task.exception() == err
