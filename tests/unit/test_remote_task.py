# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains the pytest tests for the remote tasks."""

import time
from typing import List, Optional
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.device_proxy import PstDeviceProxy
from ska_pst_lmc.util.remote_task import AggregateRemoteTask, RemoteTask


@pytest.fixture
def device_proxy() -> PstDeviceProxy:
    """Generate a device proxy fixture.

    This is a MagicMock class.
    """
    return MagicMock()


# tests that handle action result (this should be parametrised)
@pytest.mark.parametrize(
    "result_code, details, state, progress",
    [
        (ResultCode.OK, "Done", TaskStatus.COMPLETED, 100),
        (ResultCode.QUEUED, "Command ID", TaskStatus.QUEUED, 0),
        (ResultCode.REJECTED, "Not allowed", TaskStatus.REJECTED, None),
    ],
)
def test_calling_task_action(
    device_proxy: PstDeviceProxy,
    result_code: ResultCode,
    details: str,
    state: TaskStatus,
    progress: Optional[int],
) -> None:
    """Test calling the task action.

    Checks to see that the return state is mapped correctly
    based on the result code of calling the action on the device.

    :param device_proxy: the device under test.
    :param result_code: the result code of calling the device action.
    :param details: the detaile message from calling the device action.
    :param state: the expected state to be returned.
    :param progress: the expected progress value after executing task.
    """
    action = MagicMock(return_value=(result_code, details))
    task_callback = MagicMock()

    task = RemoteTask(
        device=device_proxy,
        action=action,
        task_callback=task_callback,
    )

    (out_state, out_details) = task()

    assert out_state == state
    assert out_details == details

    if result_code == ResultCode.QUEUED:
        assert task.command_id == details

    assert task.progress == progress


# test to check update of status (when id is or isn't our subscription)
@pytest.mark.parametrize(
    "command_id, curr_status, status_values, callback_called",
    [
        (None, TaskStatus.STAGING, ["1", TaskStatus.IN_PROGRESS.name], False),
        ("1", TaskStatus.STAGING, ["1", TaskStatus.IN_PROGRESS.name], True),
        ("1", TaskStatus.IN_PROGRESS, ["1", TaskStatus.IN_PROGRESS.name], False),
        ("2", TaskStatus.IN_PROGRESS, ["1", TaskStatus.IN_PROGRESS.name], False),
    ],
)
def test_status_change_subscription(
    device_proxy: PstDeviceProxy,
    command_id: str,
    curr_status: TaskStatus,
    status_values: List[str],
    callback_called: bool,
) -> None:
    """Test status change event subscription.

    Checks to see if the status change happens via event subscription.
    Only changes for the current command will cause an update. If the
    command id not in the response this currently will ignore the result.

    :param device_proxy: the device under test.
    :param command_id: the command id for long running command.
    :param curr_status: current status of long running command.
    :param status_values: the status values of the event, converted to map.
    :param callback_called: assertion of if callback should be called.
    """
    action = MagicMock()
    task_callback = MagicMock()

    task = RemoteTask(
        device=device_proxy,
        action=action,
        task_callback=task_callback,
    )
    task.command_id = command_id
    task.status = curr_status

    calls = [
        call("longRunningCommandStatus", task._status_callback),
        call("longRunningCommandProgress", task._progress_callback),
    ]
    device_proxy.subscribe_change_event.has_calls(calls)  # type: ignore

    task._status_callback(status_values)

    if callback_called:
        assert task.status == TaskStatus.IN_PROGRESS
        task.task_callback.assert_called_once_with(status=TaskStatus.IN_PROGRESS)  # type: ignore
    else:
        task.task_callback.assert_not_called()  # type: ignore
        assert task.status == curr_status


@pytest.mark.parametrize(
    "command_id, curr_progress, progress_values, callback_called",
    [
        (None, None, ["1", "25"], False),
        ("1", 25, ["1", "50"], True),
        ("1", 25, ["1", "25"], False),
        ("2", 50, ["1", "25"], False),
    ],
)
def test_progress_change_subscription(
    device_proxy: PstDeviceProxy,
    command_id: str,
    curr_progress: TaskStatus,
    progress_values: List[str],
    callback_called: bool,
) -> None:
    """Test progress change event subscription.

    Checks to see if the progress change happens via event subscription.
    Only changes for the current command will cause an update. If the
    command id not in the response this currently will ignore the result.

    :param device_proxy: the device under test.
    :param command_id: the command id for long running command.
    :param curr_progress: current progress of long running command.
    :param progress_values: the progress values of the event, converted to map.
    :param callback_called: assertion of if callback should be called.
    """
    action = MagicMock()
    task_callback = MagicMock()

    task = RemoteTask(
        device=device_proxy,
        action=action,
        task_callback=task_callback,
    )
    task.command_id = command_id
    task.progress = curr_progress

    calls = [
        call("longRunningCommandStatus", task._status_callback),
        call("longRunningCommandProgress", task._progress_callback),
    ]
    device_proxy.subscribe_change_event.has_calls(calls)  # type: ignore

    task._progress_callback(progress_values)

    if callback_called:
        assert task.progress == 50
        task.task_callback.assert_called_once_with(progress=50)  # type: ignore
    else:
        task.task_callback.assert_not_called()  # type: ignore
        assert task.progress == curr_progress


@pytest.mark.parametrize(
    "task_1_status, task_1_progress, task_2_status, task_2_progress, status, progress",
    [
        (TaskStatus.STAGING, None, TaskStatus.COMPLETED, 100, TaskStatus.STAGING, 50),
        (TaskStatus.STAGING, None, TaskStatus.IN_PROGRESS, 0, TaskStatus.IN_PROGRESS, 0),
        (TaskStatus.IN_PROGRESS, 30, TaskStatus.IN_PROGRESS, 50, TaskStatus.IN_PROGRESS, 40),
        (TaskStatus.COMPLETED, 100, TaskStatus.COMPLETED, 95, TaskStatus.COMPLETED, 100),
    ],
)
def test_aggregate_remote_task_updated(
    device_proxy: PstDeviceProxy,
    task_1_status: TaskStatus,
    task_1_progress: Optional[int],
    task_2_status: TaskStatus,
    task_2_progress: Optional[int],
    status: TaskStatus,
    progress: int,
) -> None:
    """Test AggregateRemoteTask calls the callback when remote tasks are updated.

    This checks the the calculated progress and status is a combination of the
    individual tasks.

    :param device_proxy: the device under test.
    :param task_1_status: status of first task.
    :param task_1_progress: progress of first task.
    :param task_2_status: status of second task.
    :param task_2_progress: progress of second task.
    :param status: status of overrall task.
    :param progress: progress of overall task.
    """
    task_callback = MagicMock()
    aggregate_remote_task = AggregateRemoteTask(task_callback=task_callback)

    task1 = aggregate_remote_task.add_remote_task(device=device_proxy, action=MagicMock())
    task1.status = task_1_status
    task1.progress = task_1_progress

    task2 = aggregate_remote_task.add_remote_task(device=device_proxy, action=MagicMock())
    task2.status = task_2_status
    task2.progress = task_2_progress

    aggregate_remote_task._remote_task_updated()
    task_callback.assert_called_once_with(progress=progress, status=status)


def test_if_one_task_is_rejected_aggregate_is_rejected(device_proxy: PstDeviceProxy) -> None:
    """Test AggregateRemoteTask sets state to reject if a sub-task is rejected."""
    task_callback = MagicMock()
    aggregate_remote_task = AggregateRemoteTask(task_callback=task_callback)

    aggregate_remote_task.add_remote_task(
        device=device_proxy, action=lambda _: (ResultCode.QUEUED, "command_id")
    )

    aggregate_remote_task.add_remote_task(
        device=device_proxy, action=lambda _: (ResultCode.REJECTED, "Not allowed")
    )

    (result, details) = aggregate_remote_task()
    assert result == TaskStatus.QUEUED
    assert details == "Queued"
    time.sleep(0.1)

    calls = [call(status=TaskStatus.IN_PROGRESS, progress=0), call(status=TaskStatus.REJECTED)]

    task_callback.assert_has_calls(calls)


def test_aggregate_task_should_run_to_completion(device_proxy: PstDeviceProxy) -> None:
    """Test AggregateRemoteTask background task should run to completion."""
    task_callback = MagicMock()
    aggregate_remote_task = AggregateRemoteTask(task_callback=task_callback)

    task1 = aggregate_remote_task.add_remote_task(
        device=device_proxy, action=lambda _: (ResultCode.QUEUED, "command_id_1")
    )

    task2 = aggregate_remote_task.add_remote_task(
        device=device_proxy, action=lambda _: (ResultCode.QUEUED, "command_id_2")
    )

    (result, details) = aggregate_remote_task()
    assert result == TaskStatus.QUEUED
    assert details == "Queued"

    time.sleep(0.1)

    assert aggregate_remote_task.status == TaskStatus.IN_PROGRESS

    time.sleep(0.1)

    task2.status = TaskStatus.COMPLETED
    task2.progress = 100
    task2.task_callback()
    time.sleep(0.1)

    assert not aggregate_remote_task._completed

    task1.status = TaskStatus.COMPLETED
    task1.progress = 100
    task1.task_callback()
    time.sleep(0.2)
    assert aggregate_remote_task._completed
