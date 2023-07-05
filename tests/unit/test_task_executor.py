# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains the pytest tests for the BackgroundTask class."""
from __future__ import annotations

import json
import threading
from typing import Any, Callable, List, Optional, Tuple, cast
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.device_proxy import PstDeviceProxy
from ska_pst_lmc.job import (
    DeviceAction,
    DeviceCommandTask,
    DeviceCommandTaskExecutor,
    ParallelTask,
    SequentialTask,
    TaskExecutor,
)


@pytest.fixture
def smrb_proxy() -> MagicMock:
    """Create mock fixture for SMRB device."""
    proxy = MagicMock()
    proxy.__repr__ = MagicMock(return_value="PstDeviceProxy('test/smrb/01')")  # type: ignore
    return proxy


@pytest.fixture
def recv_proxy() -> MagicMock:
    """Create mock fixture for RECV device."""
    proxy = MagicMock()
    proxy.__repr__ = MagicMock(return_value="PstDeviceProxy('test/recv/01')")  # type: ignore
    return proxy


@pytest.fixture
def dsp_proxy() -> MagicMock:
    """Create mock fixture for DSP device."""
    proxy = MagicMock()
    proxy.__repr__ = MagicMock(return_value="PstDeviceProxy('test/dsp/01')")  # type: ignore
    return proxy


@pytest.fixture
def mock_task_callback() -> MagicMock:
    """Create mock fixture to use for asserting task callbacks."""
    return MagicMock()


def _complete_job_side_effect(
    device_command_task_executor: DeviceCommandTaskExecutor,
    result: Any = "Complete",
) -> Callable[..., Tuple[List[TaskStatus], List[Optional[str]]]]:
    """
    Create a complete job side effect.

    This is used to stub out completion of remote jobs.
    """

    def _side_effect(*arg: Any, **kwargs: Any) -> Tuple[List[TaskStatus], List[Optional[str]]]:
        import uuid

        job_id = str(uuid.uuid4())

        def _complete_job() -> None:
            device_command_task_executor._handle_subscription_event((job_id, json.dumps(result)))

        threading.Thread(target=_complete_job).start()

        return ([TaskStatus.QUEUED], [job_id])

    return _side_effect


def _fail_job_side_effect(
    device_command_task_executor: DeviceCommandTaskExecutor,
    failure_message: str,
) -> Callable[..., Tuple[List[TaskStatus], List[Optional[str]]]]:
    """
    Create a complete job side effect.

    This is used to stub out completion of remote jobs.
    """

    def _side_effect(*arg: Any, **kwds: Any) -> Tuple[List[TaskStatus], List[Optional[str]]]:
        import uuid

        job_id = str(uuid.uuid4())

        def _fail_job() -> None:
            device_command_task_executor._handle_subscription_event((job_id, failure_message))

        threading.Thread(target=_fail_job).start()

        return ([TaskStatus.QUEUED], [job_id])

    return _side_effect


def test_task_executor_successfully_handles_simple_device_command_job(
    task_executor: TaskExecutor,
    device_command_task_executor: DeviceCommandTaskExecutor,
    smrb_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor handles simple jobs."""
    action = MagicMock()
    action.side_effect = _complete_job_side_effect(
        device_command_task_executor=device_command_task_executor,
        result={"foo": "bar"},
    )

    job = DeviceCommandTask(
        devices=[cast(PstDeviceProxy, smrb_proxy)],
        action=cast(DeviceAction, action),
        command_name="mock_action",
    )

    task_executor.submit_job(
        job=job,
        callback=mock_task_callback,
    )

    action.assert_called_once_with(smrb_proxy)
    mock_task_callback.assert_called_once_with(result={"foo": "bar"})


def test_task_executor_successfully_handles_device_command_job_with_multiple_devices(
    task_executor: TaskExecutor,
    device_command_task_executor: DeviceCommandTaskExecutor,
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor handles a DeviceCommandTask with multiple devices."""
    action = MagicMock()
    action.side_effect = _complete_job_side_effect(
        device_command_task_executor=device_command_task_executor,
        result={"foo": "bar"},
    )

    job = DeviceCommandTask(
        devices=[cast(PstDeviceProxy, smrb_proxy), cast(PstDeviceProxy, recv_proxy)],
        action=cast(DeviceAction, action),
        command_name="mock_action",
    )

    task_executor.submit_job(
        job=job,
        callback=mock_task_callback,
    )

    calls = [call(smrb_proxy), call(recv_proxy)]
    action.assert_has_calls(calls, any_order=True)
    mock_task_callback.assert_called_once_with(result=None)


def test_task_executor_successfully_handles_sequential_device_command_job(
    task_executor: TaskExecutor,
    device_command_task_executor: DeviceCommandTaskExecutor,
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor handles a sequential task with multiple subtasks."""
    action = MagicMock()
    action.side_effect = _complete_job_side_effect(
        device_command_task_executor=device_command_task_executor,
    )

    job = SequentialTask(
        subtasks=[
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, smrb_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, recv_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
        ]
    )

    task_executor.submit_job(
        job=job,
        callback=mock_task_callback,
    )

    calls = [call(smrb_proxy), call(recv_proxy)]
    action.assert_has_calls(calls)
    mock_task_callback.assert_called_once_with(result=None)


def test_task_executor_successfully_handles_parallel_device_command_job(
    task_executor: TaskExecutor,
    device_command_task_executor: DeviceCommandTaskExecutor,
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor handles a parallel task with multiple subtasks."""
    action = MagicMock()
    action.side_effect = _complete_job_side_effect(
        device_command_task_executor=device_command_task_executor,
    )

    job = ParallelTask(
        subtasks=[
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, smrb_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, recv_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
        ]
    )

    task_executor.submit_job(
        job=job,
        callback=mock_task_callback,
    )

    calls = [call(smrb_proxy), call(recv_proxy)]
    action.assert_has_calls(calls, any_order=True)
    mock_task_callback.assert_called_once_with(result=None)


def test_task_executor_successfully_complex_job(
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    dsp_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor handles a complex job like configure_scan in BEAM."""
    # easier to test the order of parallel calls by setting max workers to 1
    task_executor = TaskExecutor(max_parallel_workers=1)
    device_command_task_executor = task_executor._device_task_executor
    task_executor.start()

    configure_beam_action = MagicMock()
    configure_beam_action.side_effect = _complete_job_side_effect(
        device_command_task_executor=device_command_task_executor,
    )
    configure_scan_action = MagicMock()
    configure_scan_action.side_effect = _complete_job_side_effect(
        device_command_task_executor=device_command_task_executor,
    )

    # This example job comes from the configure scan on PST.BEAM
    job = SequentialTask(
        subtasks=[
            # first do configre_beam on SMRB
            DeviceCommandTask(
                devices=[smrb_proxy],
                action=configure_beam_action,
                command_name="ConfigureBeam",
            ),
            # now do configure_beam on DSP and RECV, this can be done in parallel
            DeviceCommandTask(
                devices=[dsp_proxy, recv_proxy],
                action=configure_beam_action,
                command_name="ConfigureBeam",
            ),
            # now configure scan on SMRB and RECV (smrb is no-op) in parallel
            DeviceCommandTask(
                devices=[smrb_proxy, recv_proxy],
                action=configure_scan_action,
                command_name="ConfigureScan",
            ),
            # now configure scan on the DSP device.
            DeviceCommandTask(
                devices=[dsp_proxy],
                action=configure_scan_action,
                command_name="ConfigureScan",
            ),
        ]
    )

    task_executor.submit_job(
        job=job,
        callback=mock_task_callback,
    )

    configure_beam_calls = [call(smrb_proxy), call(dsp_proxy), call(recv_proxy)]
    configure_beam_action.assert_has_calls(configure_beam_calls)

    configure_scan_calls = [call(smrb_proxy), call(recv_proxy), call(dsp_proxy)]
    configure_scan_action.assert_has_calls(configure_scan_calls)

    mock_task_callback.assert_called_once_with(result=None)

    task_executor.stop()


def test_task_executor_stops_processing_sequential_job_tasks_upon_task_failure(
    task_executor: TaskExecutor,
    device_command_task_executor: DeviceCommandTaskExecutor,
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor stops processing sequential subtasks when one fails."""
    action = MagicMock()
    action.side_effect = _fail_job_side_effect(
        device_command_task_executor=device_command_task_executor,
        failure_message="sequential job failed with first task",
    )

    job = SequentialTask(
        subtasks=[
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, smrb_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, recv_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
        ]
    )

    with pytest.raises(RuntimeError) as excinfo:
        task_executor.submit_job(
            job=job,
            callback=mock_task_callback,
        )

        assert "sequential job failed with first task" in str(excinfo.value)

    recv_proxy.assert_not_called()
    action.assert_called_once_with(smrb_proxy)


def test_task_executor_stops_processing_parallel_job_tasks_upon_task_failure(
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor stops processing parallel subtasks one fails."""
    # easier to test the parallel job code using max_workers of 1 and treating as
    # as sequential queue.
    task_executor = TaskExecutor(max_parallel_workers=1)
    device_command_task_executor = task_executor._device_task_executor
    task_executor.start()

    action = MagicMock()
    action.side_effect = _fail_job_side_effect(
        device_command_task_executor=device_command_task_executor,
        failure_message="parallel job failed with first task",
    )

    job = ParallelTask(
        subtasks=[
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, smrb_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
            DeviceCommandTask(
                devices=[cast(PstDeviceProxy, recv_proxy)],
                action=cast(DeviceAction, action),
                command_name="mock_action",
            ),
        ]
    )

    with pytest.raises(RuntimeError) as excinfo:
        task_executor.submit_job(
            job=job,
            callback=mock_task_callback,
        )

        assert "parallel job failed with first task" in str(excinfo.value)

    recv_proxy.assert_not_called()
    action.assert_called_once_with(smrb_proxy)

    task_executor.stop()


def test_device_task_executor_throws_exception_if_device_job_fails(
    task_executor: TaskExecutor,
    device_command_task_executor: DeviceCommandTaskExecutor,
    smrb_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor throws an exception when device job fails."""
    action = MagicMock()
    action.side_effect = _fail_job_side_effect(
        device_command_task_executor=device_command_task_executor,
        failure_message="job failed",
    )

    job = DeviceCommandTask(
        devices=[cast(PstDeviceProxy, smrb_proxy)],
        action=cast(DeviceAction, action),
        command_name="mock_action",
    )

    with pytest.raises(RuntimeError) as excinfo:
        task_executor.submit_job(
            job=job,
            callback=mock_task_callback,
        )

        assert "job failed" in str(excinfo.value)


def test_task_executor_stops_processing_parallel_device_command_tasks_upon_task_failure(
    smrb_proxy: MagicMock,
    recv_proxy: MagicMock,
    mock_task_callback: MagicMock,
) -> None:
    """Test that task executor throws an exception when a parallel device job fails."""
    # easier to test the parallel job code using max_workers of 1 and treating as
    # as sequential queue.
    task_executor = TaskExecutor(max_parallel_workers=1)
    device_command_task_executor = task_executor._device_task_executor
    task_executor.start()

    action = MagicMock()
    action.side_effect = _fail_job_side_effect(
        device_command_task_executor=device_command_task_executor,
        failure_message="parallel device command task failed with first task",
    )

    job = DeviceCommandTask(
        devices=[cast(PstDeviceProxy, smrb_proxy), cast(PstDeviceProxy, recv_proxy)],
        action=cast(DeviceAction, action),
        command_name="mock_action",
    )

    with pytest.raises(RuntimeError) as excinfo:
        task_executor.submit_job(
            job=job,
            callback=mock_task_callback,
        )

        assert "parallel device command task with first task" in str(excinfo.value)

    recv_proxy.assert_not_called()
    action.assert_called_once_with(smrb_proxy)

    task_executor.stop()
