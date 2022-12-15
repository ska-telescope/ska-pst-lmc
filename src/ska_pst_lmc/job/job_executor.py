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
import uuid
from typing import Dict, cast

from ska_pst_lmc.util.callback import Callback, callback_safely

from .common import DEVICE_COMMAND_JOB_QUEUE, JOB_QUEUE
from .context import (
    DeviceCommandJob,
    DeviceCommandJobContext,
    Job,
    JobContext,
    ParallelJob,
    ParallelJobContext,
    ParallelJobTaskContext,
    SequentialJob,
)

_logger = logging.getLogger(__name__)


class JobExecutor:
    """An executor class that handles requests for jobs.

    Jobs are submited to instances of this class via the :py:meth:`submit_job`
    method or to the global instance of this job executor `GLOBAL_JOB_EXECUTOR`
    via the global method `submit_job`.

    Instances of this class are linked with `DeviceCommandJobExecutor` that will
    handle the Tango logic of subscriptions and dealing with long running commands.
    But the both need to share a :py:class:`queue.Queue` for which this class will
    send messages to while the `DeviceCommandJobExecutor` will read from.
    """

    def __init__(
        self: JobExecutor,
        job_queue: queue.Queue[JobContext] = JOB_QUEUE,
        device_command_job_queue: queue.Queue[DeviceCommandJobContext] = DEVICE_COMMAND_JOB_QUEUE,
        max_parallel_workers: int = 4,
    ) -> None:
        """Initialise job executor.

        :param job_queue: queue used for main processing, defaults to JOB_QUEUE
        :type job_queue: queue.Queue, optional
        :param device_command_job_queue: queue used for sending request to a
            `DeviceCommandJobExecutor`, defaults to DEVICE_COMMAND_JOB_QUEUE
        :type device_command_job_queue: queue.Queue, optional
        :param max_parallel_workers: maximum number of workers used for parallel job
            processing.
        :type max_parallel_workers: int
        """
        self._main_job_queue = job_queue
        self._device_command_job_queue = device_command_job_queue

        self._sequential_job_queue: queue.Queue[JobContext] = queue.Queue(maxsize=1)

        self._parallel_lock = threading.Lock()
        self._parallel_job_queue: queue.Queue[ParallelJobTaskContext] = queue.Queue()
        self._parallel_job_context_map: Dict[str, ParallelJobContext] = {}

        self._max_parallel_workers = max_parallel_workers
        self._stop = threading.Event()
        self._running = False

        # need 1 worker for main queue, plus max paralled workers

    def __del__(self: JobExecutor) -> None:
        """Tear down class being destroyed."""
        self.stop()

    def __enter__(self: JobExecutor) -> JobExecutor:
        """Context manager start."""
        self.start()
        return self

    def __exit__(self: JobExecutor, exc_type: None, exc_val: None, exc_tb: None) -> None:
        """Context manager exit."""
        self.stop()

    def start(self: JobExecutor) -> None:
        """Start the job executor."""
        self._running = True
        # need to reset this each time we start.
        self._stop = threading.Event()

        self._main_tpe = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="MainJob")
        self._main_tpe.submit(self._process_main_queue)

        self._sequential_tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="SequentialJob"
        )
        self._sequential_tpe.submit(self._process_sequential_queue)

        self._parallel_tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_parallel_workers, thread_name_prefix="ParallelJob"
        )
        for _ in range(self._max_parallel_workers):
            self._parallel_tpe.submit(self._process_parallel_queue)

    def stop(self: JobExecutor) -> None:
        """Stop the executor."""
        if self._running:
            self._running = False
            self._stop.set()
            self._main_tpe.shutdown()
            self._sequential_tpe.shutdown()
            self._parallel_tpe.shutdown()

    def submit_job(self: JobExecutor, job: Job, callback: Callback = None) -> None:
        """Submit a job to be executed.

        This is the main method that clients should use to submit jobs to be
        executed. This will wrap into a `JobContext` and put it on the main
        queue which can then be processed.

        :param job: the job to be submitted, it can be a simple `DeviceCommandJob`
            or a composite job like a `SequentialJob` or `ParallelJob`.
        :type job: Job
        :param callback: the callback to notify the job is complete, defaults to None
        :type callback: Callback, optional
        """
        self._submit_job(JobContext(job=job, callback=callback))

    def _submit_job(self: JobExecutor, job_context: JobContext) -> None:
        """Submit a job context to the main execution queue.

        :param job_context: the job context object to submit.
        :type job_context: JobContext
        """
        _logger.debug(f"Submitting job with context={job_context}")
        self._main_job_queue.put(job_context)

    def _process_main_queue(self: JobExecutor) -> None:
        """Process messages on the main queue.

        This method is perfomed in the background by a thread. It will run in
        and infinite loop until the instance of this class is destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    job_context = cast(JobContext, self._main_job_queue.get(timeout=0.1))
                    _logger.debug(f"Main process loop receieved job with context={job_context}")
                    self._handle_job(job_context)
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error processing main queue", exc_info=True)

    def _process_sequential_queue(self: JobExecutor) -> None:
        """Process messages on the sequential queue.

        This method is perfomed in the background by a thread. It will run in
        and infinite loop until the instance of this class is destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    job_context = cast(JobContext, self._sequential_job_queue.get(timeout=0.1))
                    evt = threading.Event()
                    sequential_job_context = JobContext(job=job_context.job, callback=evt.set)
                    _logger.debug(f"Sequential process loop receieved job with context={job_context}")
                    self._handle_job(sequential_job_context)
                    evt.wait()
                    self._sequential_job_queue.task_done()
                    if job_context.callback:
                        job_context.callback()
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error processing sequential queue", exc_info=True)

    def _process_parallel_queue(self: JobExecutor) -> None:
        """Process messages on the parallel job queue.

        This method is perfomed in the background by a thread. It will run in
        and infinite loop until the instance of this class is destroyed.

        The threads running this are different to the main queue thread.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = self._parallel_job_queue.get(timeout=0.1)
                    _logger.debug(f"Parallel process loop receieved job with context={task_context}")
                    self._handle_parallel_task(task_context=task_context)
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error during processing parallel queue", exc_info=True)

    def _handle_sequential_job(self: JobExecutor, job: SequentialJob, callback: Callback = None) -> None:
        """Handle a `SequentialJob` request.

        This method will process a `SequentialJob` by submitting each of the individual subtasks
        as a job onto the sequential job queue to be processed, as there is only one thread processing
        that queue they are guaranteed to run sequentially.

        Only when the last task is complete will the callback be called.

        :param job: the job which subtasks need to be done sequentially.
        :type job: SequentialJob
        :param callback: callback to call once all subtasks are complete, defaults to None
        :type callback: Callback, optional
        """
        tasks = [JobContext(job=j) for j in job.tasks]

        for t in tasks:
            # wait for each subtask by using an event as the callback
            task_evt = threading.Event()
            t.callback = task_evt.set
            self._sequential_job_queue.put(t)
            task_evt.wait()

        callback_safely(callback)

    def _handle_parallel_job(self: JobExecutor, job: ParallelJob, callback: Callback = None) -> None:
        """Handle a `ParallelJob` request.

        This method will process a `ParallelJob` by submitting each indivial subtasks on to
        the internal parallel job queue. A parallel job context is used to track the overall
        progress of the job by assigning a random UUID to the whole process. Each subtask is
        also given a random UUID as well as a `threading.Event`.

        :param job: the job which subtasks can be done concurrently.
        :type job: ParallelJob
        :param callback: callback to call once all subtasks are complete, defaults to None
        :type callback: Callback, optional
        """
        job_id = str(uuid.uuid4())
        task_contexts = [
            ParallelJobTaskContext(job_id=job_id, task_id=str(uuid.uuid4()), signal=threading.Event(), job=t)
            for t in job.tasks
        ]

        job_context = ParallelJobContext(
            job_id=job_id, tasks_signals=[tc.signal for tc in task_contexts], signal=threading.Event()
        )

        with self._parallel_lock:
            self._parallel_job_context_map[job_id] = job_context
            for tc in task_contexts:
                self._parallel_job_queue.put(tc)

        job_context.signal.wait()
        callback_safely(callback)

    def _handle_parallel_task(self: JobExecutor, task_context: ParallelJobTaskContext) -> None:
        """Handle a parallel job subtask.

        This converts the `task_context` into a `JobContext` and calls the :py:meth:`_handle_job`
        method to be processed, this doesn't happen on the main thread so it won't block.

        :param task_context: the subtask context
        :type task_context: ParallelJobTaskContext
        """
        job_context = JobContext(job=task_context.job, callback=task_context.signal.set)

        self._handle_job(job_context)
        task_context.signal.wait()
        self._handle_task_complete(task_context)

    def _handle_task_complete(self: JobExecutor, task_context: ParallelJobTaskContext) -> None:
        """Handle parallel task being complete.

        :param task_context: the task context of the completed task.
        :type task_context: ParallelJobTaskContext
        """
        with self._parallel_lock:
            job_context = self._parallel_job_context_map[task_context.job_id]

            states = [s.is_set() for s in job_context.tasks_signals]
            if all(states):
                job_context.signal.set()
                del self._parallel_job_context_map[task_context.job_id]

    def _handle_device_command_job(
        self: JobExecutor, job: DeviceCommandJob, callback: Callback = None
    ) -> None:
        """Handle a device command job.

        This method handles a `DeviceCommandJob`, if there is just one device this sent to a
        :py:class:`DeviceCommandJobExecutor` via a queue. If ther are multiple devices this is
        converted into a `ParallelJob` with separate `DeviceCommandJob` jobs to be handled,
        which ultimately come back to this method but will then be sent to the `DeviceCommandJobExecutor`.

        :param job: the remove device command to run.
        :type job: DeviceCommandJob
        :param callback: callback to call once all device commands are complete, defaults to None
        :type callback: Callback, optional
        """
        try:
            evt = threading.Event()
            if len(job.devices) > 1:
                # run this as a parallel job, this will reenter this method but fall into the else
                parallel_job = ParallelJob(
                    tasks=[
                        DeviceCommandJob(devices=[d], action=job.action, command_name=job.command_name)
                        for d in job.devices
                    ]
                )
                self._handle_parallel_job(job=parallel_job, callback=evt.set)
            else:
                device_job_context = DeviceCommandJobContext(
                    device=job.devices[0], action=job.action, signal=evt, command_name=job.command_name
                )
                _logger.debug(f"Submitting {device_job_context} to device command job queue.")
                self._device_command_job_queue.put(device_job_context)

            evt.wait()
            callback_safely(callback)
        except Exception:
            _logger.exception("Error and handling DeviceCommandJob", exc_info=True)

    def _handle_job(self: JobExecutor, job_context: JobContext) -> None:
        """Handle a job.

        This is an internal method that is used by the background threads to
        route the job to the correct handler.

        :param job_context: the context of the job to run.
        :type job_context: JobContext
        """
        job = job_context.job
        callback = job_context.callback

        if type(job) == SequentialJob:
            self._handle_sequential_job(cast(SequentialJob, job), callback)

        elif type(job) == ParallelJob:
            self._handle_parallel_job(cast(ParallelJob, job), callback)

        elif type(job) == DeviceCommandJob:
            self._handle_device_command_job(cast(DeviceCommandJob, job), callback)


JOB_EXECUTOR: JobExecutor = JobExecutor()
"""Global :py:class:`JobExecutor`.

This should be used alongside the global `DeviceCommandJobExecutor`.
"""


def submit_job(job: Job, callback: Callback = None) -> None:
    """Submit a job to the global `JobExecutor`.

    :param job: the job to submit.
    :type job: Job
    :param callback: callback to use when job completes, defaults to None
    :type callback: Callback, optional
    """
    from .device_task_executor import DEVICE_COMMAND_JOB_EXECUTOR

    # ensure the executors are running, there is an atexit
    # to ensure they are stopped.
    JOB_EXECUTOR.start()
    DEVICE_COMMAND_JOB_EXECUTOR.start()

    JOB_EXECUTOR.submit_job(job=job, callback=callback)


atexit.register(JOB_EXECUTOR.stop)
