# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for handling long running jobs."""

from __future__ import annotations

import atexit
import concurrent.futures
import logging
import queue
import threading
from typing import Dict, cast

from ska_pst_lmc.util.callback import Callback

from .common import DEVICE_COMMAND_JOB_QUEUE, TASK_QUEUE
from .context import (
    DeviceCommandTask,
    DeviceCommandTaskContext,
    JobContext,
    ParallelTask,
    ParallelTaskContext,
    SequentialTask,
    Task,
    TaskContext,
)

_logger = logging.getLogger(__name__)


class TaskExecutor:
    """An executor class that handles requests for jobs.

    Jobs are submited to instances of this class via the :py:meth:`submit_job`
    method or to the global instance of this job executor `GLOBAL_JOB_EXECUTOR`
    via the global method `submit_job`.

    Instances of this class are linked with `DeviceCommandTaskExecutor` that will
    handle the Tango logic of subscriptions and dealing with long running commands.
    But the both need to share a :py:class:`queue.Queue` for which this class will
    send messages to while the `DeviceCommandTaskExecutor` will read from.
    """

    def __init__(
        self: TaskExecutor,
        task_queue: queue.Queue[TaskContext] = TASK_QUEUE,
        device_command_task_queue: queue.Queue[DeviceCommandTaskContext] = DEVICE_COMMAND_JOB_QUEUE,
        max_parallel_workers: int = 4,
    ) -> None:
        """Initialise job executor.

        :param task_queue: queue used for main processing, defaults to JOB_QUEUE
        :type task_queue: queue.Queue, optional
        :param device_command_task_queue: queue used for sending request to a
            `DeviceCommandTaskExecutor`, defaults to DEVICE_COMMAND_JOB_QUEUE
        :type device_command_task_queue: queue.Queue, optional
        :param max_parallel_workers: maximum number of workers used for parallel job
            processing.
        :type max_parallel_workers: int
        """
        self._main_task_queue = task_queue
        self._device_command_task_queue = device_command_task_queue

        self._sequential_task_queue: queue.Queue[TaskContext] = queue.Queue(maxsize=1)

        self._parallel_lock = threading.Lock()
        self._parallel_task_queue: queue.Queue[ParallelTaskTaskContext] = queue.Queue()
        self._parallel_task_context_map: Dict[str, ParallelTaskContext] = {}

        self._max_parallel_workers = max_parallel_workers
        self._stop = threading.Event()
        self._running = False

        # need 1 worker for main queue, plus max paralled workers

    def __del__(self: TaskExecutor) -> None:
        """Tear down class being destroyed."""
        self.stop()

    def __enter__(self: TaskExecutor) -> TaskExecutor:
        """Context manager start."""
        self.start()
        return self

    def __exit__(self: TaskExecutor, exc_type: None, exc_val: None, exc_tb: None) -> None:
        """Context manager exit."""
        self.stop()

    def start(self: TaskExecutor) -> None:
        """Start the job executor."""
        self._running = True
        # need to reset this each time we start.
        self._stop = threading.Event()

        self._main_tpe = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="MainJob")
        self._main_tpe.submit(self._process_main_queue)

        self._sequential_tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="SequentialTask"
        )
        self._sequential_tpe.submit(self._process_sequential_queue)

        self._parallel_tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_parallel_workers, thread_name_prefix="ParallelTask"
        )
        for _ in range(self._max_parallel_workers):
            self._parallel_tpe.submit(self._process_parallel_queue)

    def stop(self: TaskExecutor) -> None:
        """Stop the executor."""
        if self._running:
            self._running = False
            self._stop.set()
            self._main_tpe.shutdown()
            self._sequential_tpe.shutdown()
            self._parallel_tpe.shutdown()

    def submit_job(self: TaskExecutor, job: Task, callback: Callback = None) -> None:
        """Submit a job to be executed.

        This is the main method that clients should use to submit jobs to be
        executed. This will wrap into a `TaskContext` and put it on the main
        queue which can then be processed.

        :param job: the job to be submitted, it can be a simple `DeviceCommandTask`
            or a composite job like a `SequentialTask` or `ParallelTask`.
        :type job: Job
        :param callback: the callback to notify the job is complete, defaults to None
        :type callback: Callback, optional
        """
        self._submit_job(JobContext(task=job, success_callback=callback))

    def _submit_job(self: TaskExecutor, task_context: JobContext) -> None:
        """Submit a root task context to the main execution queue.

        :param task_context: the job context object to submit.
        :type task_context: TaskContext
        """
        _logger.debug(f"Submitting job with context={task_context}")
        self._main_task_queue.put(task_context)

    def _process_main_queue(self: TaskExecutor) -> None:
        """Process messages on the main queue.

        This method is perfomed in the background by a thread. It will run in
        and infinite loop until the instance of this class is destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = cast(JobContext, self._main_task_queue.get(timeout=0.1))
                    _logger.debug(f"Main process loop receieved job with context={task_context}")
                    self._handle_task(task_context)
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error processing main queue", exc_info=True)

    def _process_sequential_queue(self: TaskExecutor) -> None:
        """Process messages on the sequential queue.

        This method is perfomed in the background by a thread. It will run in
        and infinite loop until the instance of this class is destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = cast(TaskContext, self._sequential_task_queue.get(timeout=0.1))
                    # evt = threading.Event()
                    # sequential_task_context = TaskContext(job=task_context.job, callback=evt.set)
                    _logger.debug(f"Sequential process loop receieved job with context={task_context}")
                    self._handle_task(task_context)
                    task_context.evt.wait()

                    self._sequential_task_queue.task_done()
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error processing sequential queue", exc_info=True)

    def _process_parallel_queue(self: TaskExecutor) -> None:
        """Process messages on the parallel job queue.

        This method is perfomed in the background by a thread. It will run in
        and infinite loop until the instance of this class is destroyed.

        The threads running this are different to the main queue thread.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = self._parallel_task_queue.get(timeout=0.1)
                    _logger.debug(f"Parallel process loop receieved task with context={task_context}")
                    self._handle_parallel_subtask(task_context=task_context)
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error during processing parallel queue", exc_info=True)

    def _handle_sequential_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """Handle a `SequentialTask` request.

        This method will process a `SequentialTask` by submitting each of the individual subtasks
        as a task onto the sequential task queue to be processed, as there is only one thread processing
        that queue they are guaranteed to run sequentially.

        Only when the last task is complete will the callback be called.

        :param job: the job which subtasks need to be done sequentially.
        :type job: SequentialTask
        :param callback: callback to call once all subtasks are complete, defaults to None
        :type callback: Callback, optional
        """
        task = cast(SequentialTask, task_context.task)
        subtasks = [TaskContext(task=t, parent_task_context=task_context) for t in task.subtasks]

        for t in subtasks:
            # wait for each subtask by using an event as the callback
            self._sequential_task_queue.put(t)
            t.evt.wait()

            if t.failed:
                # stop processing
                task_context.signal_failed(exception=t.exception)
                break

        if not task_context.failed:
            task_context.signal_complete()

    def _handle_parallel_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """Handle a parallel task.

        This method will process a `ParallelTask` by submitting each indivial subtasks on to
        the internal parallel job queue. A parallel job context is used to track the overall
        progress of the job by assigning a random UUID to the whole process. Each subtask is
        also given a random UUID as well as a `threading.Event`.

        :param job: the job which subtasks can be done concurrently.
        :type job: ParallelTask
        :param callback: callback to call once all subtasks are complete, defaults to None
        :type callback: Callback, optional
        """
        # task_contexts = [
        #     ParallelTaskTaskContext(job_id=job_id, task_id=str(uuid.uuid4()), signal=threading.Event(), job=t)
        #     for t in job.tasks
        # ]
        task = cast(ParallelTask, task_context.task)
        parallel_task_context = ParallelTaskContext(
            task=task,
            parent_task_context=task_context,
        )

        parallel_task_context.subtasks = [
            TaskContext(task=t, parent_task_context=parallel_task_context) for t in task.subtasks
        ]

        with self._parallel_lock:
            for tc in parallel_task_context.subtasks:
                self._parallel_task_queue.put(tc)

        # block while waiting for subtasks
        parallel_task_context.evt.wait()

        if parallel_task_context.failed:
            task_context.signal_failed(parallel_task_context.exception)
        else:
            task_context.signal_complete()

    def _handle_parallel_subtask(self: TaskExecutor, task_context: TaskContext) -> None:
        """Handle a parallel subtask.

        This converts the `task_context` into a `TaskContext` and calls the :py:meth:`_handle_job`
        method to be processed, this doesn't happen on the main thread so it won't block.

        :param task_context: the subtask context
        :type task_context: TaskContext
        """
        parent_task_context = cast(ParallelTaskContext, task_context.parent_task_context)
        if parent_task_context.failed:
            # Parent has already been marked as failed.  Avoid processing any further
            return

        self._handle_task(task_context)

        # wait unilt subtask completes
        task_context.evt.wait()

        with self._parallel_lock:
            if task_context.failed and not parent_task_context.failed:
                parent_task_context.signal_failed(exception=task_context.exception)

            if parent_task_context.failed:
                return

            states = [st.completed for st in parent_task_context.subtasks]

            if all(states) and not parent_task_context.completed:
                parent_task_context.signal_complete()

    def _handle_device_command_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """Handle a device command task.

        This method handles a `DeviceCommandTask`, if there is just one device this sent to a
        :py:class:`DeviceCommandTaskExecutor` via a queue. If ther are multiple devices this is
        converted into a `ParallelTask` with separate `DeviceCommandTask` tasks to be handled,
        which ultimately come back to this method but will then be sent to the `DeviceCommandTaskExecutor`.

        :param job: the remove device command to run.
        :type job: DeviceCommandTask
        :param callback: callback to call once all device commands are complete, defaults to None
        :type callback: Callback, optional
        """
        task = cast(DeviceCommandTask, task_context.task)
        if len(task.devices) > 1:
            # run this as a parallel task, this will reenter this method but fall into the else
            parallel_task = ParallelTask(
                subtasks=[
                    DeviceCommandTask(devices=[d], action=task.action, command_name=task.command_name)
                    for d in task.devices
                ]
            )
            child_task_context = parallel_task_context = TaskContext(
                task=parallel_task,
                parent_task_context=task_context,
            )
            self._handle_parallel_task(parallel_task_context)
        else:
            child_task_context = device_task_context = DeviceCommandTaskContext(
                task=task, device=task.devices[0], action=task.action, command_name=task.command_name
            )
            _logger.debug(f"Submitting {device_task_context} to device command job queue.")
            self._device_command_task_queue.put(device_task_context)

        child_task_context.evt.wait()
        if child_task_context.failed:
            task_context.signal_failed(exception=child_task_context.exception)
        else:
            task_context.signal_complete(result=child_task_context.result)

    def _handle_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """Handle a task.

        This is an internal method that is used by the background threads to
        route the tasks to the correct handler.

        :param task_context: the context of the task to run.
        :type task_context: TaskContext
        """
        task = task_context.task

        if type(task) == SequentialTask:
            self._handle_sequential_task(task_context)

        elif type(task) == ParallelTask:
            self._handle_parallel_task(task_context)

        elif type(task) == DeviceCommandTask:
            self._handle_device_command_task(task_context)


TASK_EXECUTOR: TaskExecutor = TaskExecutor()
"""Global :py:class:`JobExecutor`.

This should be used alongside the global `DeviceCommandTaskExecutor`.
"""


def submit_job(job: Task, callback: Callback = None) -> None:
    """Submit a job to the global `JobExecutor`.

    :param job: the job to submit.
    :type job: Job
    :param callback: callback to use when job completes, defaults to None
    :type callback: Callback, optional
    """
    from .device_task_executor import DEVICE_COMMAND_TASK_EXECUTOR

    # ensure the executors are running, there is an atexit
    # to ensure they are stopped.
    TASK_EXECUTOR.start()
    DEVICE_COMMAND_TASK_EXECUTOR.start()

    TASK_EXECUTOR.submit_job(job=job, callback=callback)


atexit.register(TASK_EXECUTOR.stop)
