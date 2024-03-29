# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for handling long running jobs."""

from __future__ import annotations

import concurrent.futures
import logging
import queue
import threading
from typing import Callable, Dict, Optional, Type, cast

from ska_pst_lmc.job.device_task_executor import DeviceCommandTaskExecutor
from ska_pst_lmc.job.task import (
    DeviceCommandTask,
    DeviceCommandTaskContext,
    JobContext,
    LambdaTask,
    NoopTask,
    ParallelTask,
    ParallelTaskContext,
    SequentialTask,
    Task,
    TaskContext,
)
from ska_pst_lmc.util.callback import Callback, callback_safely

_logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    An executor class that handles requests for tasks.

    Jobs are submitted to instances of this class via the :py:meth:`submit_job`
    method or to the global instance of this task executor `GLOBAL_JOB_EXECUTOR`
    via the global method `submit_job`.

    Instances of this class are linked with `DeviceCommandTaskExecutor` that will
    handle the TANGO logic of subscriptions and dealing with long running commands.
    Both need to share an instance of a :py:class:`queue.Queue` for which this class
    will send messages to while the `DeviceCommandTaskExecutor` will read from.
    """

    def __init__(
        self: TaskExecutor,
        job_queue: Optional[queue.Queue[TaskContext]] = None,
        device_command_task_queue: Optional[queue.Queue[DeviceCommandTaskContext]] = None,
        max_parallel_workers: int = 4,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialise task executor.

        :param job_queue: queue used for main processing of jobs, defaults to None
        :type job_queue: queue.Queue, optional
        :param device_command_task_queue: queue used for sending request to a
            `DeviceCommandTaskExecutor`, defaults to None
        :type device_command_task_queue: queue.Queue, optional
        :param max_parallel_workers: maximum number of workers used for parallel task
            processing.
        :type max_parallel_workers: int
        """
        self._logger = logger or logging.getLogger(__name__)
        self._main_task_queue = job_queue or queue.Queue()
        self._device_command_task_queue = device_command_task_queue or queue.Queue()

        self._sequential_task_queue: queue.Queue[TaskContext] = queue.Queue(maxsize=1)

        self._parallel_lock = threading.Lock()
        self._parallel_task_queue: queue.Queue[TaskContext] = queue.Queue()

        self._max_parallel_workers = max_parallel_workers
        self._stop = threading.Event()
        self._running = False

        self.task_routing_map: Dict[Type[Task], Callable[[TaskContext], None]] = {
            NoopTask: self._handle_noop_task,
            SequentialTask: self._handle_sequential_task,
            ParallelTask: self._handle_parallel_task,
            DeviceCommandTask: self._handle_device_command_task,
            LambdaTask: self._handle_lambda_task,
        }

        self._device_task_executor = DeviceCommandTaskExecutor(
            task_queue=self._device_command_task_queue, logger=self._logger
        )

    def __del__(self: TaskExecutor) -> None:
        """Tear down class being destroyed."""
        self.stop()

    def start(self: TaskExecutor) -> None:
        """Start the task executor."""
        self._device_task_executor.start()

        if self._running:
            # don't start the executor again
            return

        self._running = True
        # need to reset this each time we start.
        self._stop = threading.Event()

        self._main_tpe = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="JobThread")
        self._main_tpe.submit(self._process_main_queue)

        self._sequential_tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="SequentialTaskThread"
        )
        self._sequential_tpe.submit(self._process_sequential_queue)

        self._parallel_tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_parallel_workers, thread_name_prefix="ParallelTaskThread"
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

        self._device_task_executor.stop()

    def submit_job(self: TaskExecutor, job: Task, callback: Callback = None) -> None:
        """
        Submit a job to be executed.

        This is the main method that clients should use to submit jobs to be
        executed. This will wrap into a `TaskContext` and put it on the main
        queue which can then be processed.

        :param job: the job to be submitted, it can be a simple `DeviceCommandTask`
            or a composite task like a `SequentialTask` or `ParallelTask`.
        :type job: Task
        :param callback: the callback to notify the job is complete, defaults to None
        :type callback: Callback, optional
        """
        self._submit_job(JobContext(task=job, success_callback=callback))

    def _submit_job(self: TaskExecutor, task_context: JobContext) -> None:
        """
        Submit a root task context to the main execution queue.

        :param task_context: the job context object to submit.
        :type task_context: JobContext
        """
        self._logger.debug(f"Submitting job with context={task_context}")
        self._main_task_queue.put(task_context)

        # want to wait until job has completed
        task_context.evt.wait()

        if task_context.failed:
            raise task_context.exception  # type: ignore
        else:
            callback_safely(task_context.success_callback, result=task_context.result)

    def _process_main_queue(self: TaskExecutor) -> None:
        """
        Process messages on the main queue.

        This method is perfomed in the background by a thread. It will run in and infinite loop until the
        instance of this class is destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = cast(JobContext, self._main_task_queue.get(timeout=0.1))
                    self._logger.debug(f"Main process loop received job with context={task_context}")
                    self._route_task(task_context)
                except queue.Empty:
                    continue
        except Exception:
            self._logger.exception("Error processing main queue", exc_info=True)

    def _process_sequential_queue(self: TaskExecutor) -> None:
        """
        Process messages on the sequential queue.

        This method is perfomed in the background by a thread. It will run in and infinite loop until the
        instance of this class is destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = cast(TaskContext, self._sequential_task_queue.get(timeout=0.1))
                    self._logger.debug(f"Sequential process loop received task with context={task_context}")
                    self._route_task(task_context)
                    self._logger.debug(f"Awaiting for sequential task {task_context.task_id} to complete")
                    task_context.evt.wait()
                    self._logger.debug(f"Sequential task {task_context.task_id} is complete.")

                    self._sequential_task_queue.task_done()
                except queue.Empty:
                    continue
        except Exception:
            self._logger.exception("Error processing sequential queue", exc_info=True)

    def _process_parallel_queue(self: TaskExecutor) -> None:
        """
        Process messages on the parallel task queue.

        This method is perfomed in the background by a thread. It will run in and infinite loop until the
        instance of this class is destroyed.

        The threads running this are different to the main queue thread.
        """
        try:
            while not self._stop.is_set():
                try:
                    task_context = self._parallel_task_queue.get(timeout=0.1)
                    self._logger.debug(f"Parallel process loop received task with context={task_context}")
                    self._handle_parallel_subtask(task_context=task_context)
                except queue.Empty:
                    continue
        except Exception:
            self._logger.exception("Error during processing parallel queue", exc_info=True)

    def _handle_sequential_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Handle a sequential task request.

        The `task_context` passed to this method has a `task` of type `SequentialTask`. This
        will process the sequential task by submitting each of the individual subtasks
        as a task onto the sequential task queue to be processed, as there is only one thread
        processing that queue they are guaranteed to run sequentially.

        Only when the last task is complete will the callback be called.

        If any subtask fails then the remaining subtasks will not be executed and the
        `task_context` passed in will be marked as failed with the exception that occured
        in the subtask that failed.

        :param task_context: the task_context which subtasks need to be done sequentially.
        :type task_context: TaskContext
        """
        task = cast(SequentialTask, task_context.task)
        self._logger.debug(f"Received sequential task: {task_context}")
        subtasks = [TaskContext(task=t, parent_task_context=task_context) for t in task.subtasks]

        for t in subtasks:
            # wait for each subtask by using an event as the callback
            self._logger.debug(f"Submitting subtask {t.task_id} for parent {task_context.task_id}")
            self._sequential_task_queue.put(t)

            # wait for subtask to complete or fail
            self._logger.debug(f"Waiting subtask {t.task_id} for parent {task_context.task_id}")
            t.evt.wait()
            self._logger.debug(f"Subtask {t.task_id} for parent {task_context.task_id} complete")

            if t.failed:
                # signal overall task is failed and stop processing
                self._logger.debug(
                    f"Subtask {t.task_id} for parent {task_context.task_id} failed marking task as failed"
                )
                task_context.signal_failed(exception=t.exception)  # type: ignore
                break

        if not task_context.failed:
            self._logger.debug(f"All subtasks of {task_context.task_id} completed successfully")
            task_context.signal_complete()

    def _handle_parallel_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Handle a parallel task.

        This method will process a `ParallelTask` by submitting each individual subtasks on to
        the internal parallel task queue. The overall task is not considered complete until all
        the subtasks are complete.  If any of the subtasks fail no new subtasks of the overall
        task will be processed but the subtasks already running may run to completion.

        If any subtask fails then the overall task will be marked as failed with the exception
        that happened in the first subtask that failed.

        :param task_context: the task context which its subtasks can be done concurrently.
        :type task_context: TaskContext
        """
        task = cast(ParallelTask, task_context.task)
        self._logger.debug(f"Received parallel task: {task_context}")
        parallel_task_context = ParallelTaskContext(
            task=task,
            parent_task_context=task_context,
        )

        parallel_task_context.subtasks = [
            TaskContext(task=t, parent_task_context=parallel_task_context) for t in task.subtasks
        ]
        self._logger.debug(f"Create parallel task context: {parallel_task_context.task_id}")

        with self._parallel_lock:
            self._logger.debug(f"Submitting subtasks for {parallel_task_context.task_id}")

            for tc in parallel_task_context.subtasks:
                self._parallel_task_queue.put(tc)

        # block while waiting for subtasks
        self._logger.debug(f"Awaiting subtasks for {parallel_task_context.task_id}")
        parallel_task_context.evt.wait()
        self._logger.debug(f"All subtasks for {parallel_task_context.task_id} have completed")

        if parallel_task_context.failed:
            self._logger.debug(
                f"Task {parallel_task_context.task_id} failed marking {task_context.task_id} as failed"
            )
            task_context.signal_failed(parallel_task_context.exception)  # type: ignore
        else:
            self._logger.debug(
                (
                    f"Task {parallel_task_context.task_id} completed successfully."
                    f"Marking {task_context.task_id} as complete"
                )
            )
            task_context.signal_complete()

    def _handle_parallel_subtask(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Handle a parallel subtask.

        This converts the `task_context` into a `TaskContext` and calls the :py:meth:`_handle_task`
        method to be processed, this doesn't happen on the main thread so it won't block.

        :param task_context: the subtask context
        :type task_context: TaskContext
        """
        parent_task_context = cast(ParallelTaskContext, task_context.parent_task_context)
        self._logger.debug(f"Parallel subtask {task_context.task_id} received.")

        if parent_task_context.failed:
            # Parent has already been marked as failed.  Avoid processing any further
            self._logger.debug(
                f"Parallel subtask {task_context.task_id} parent already marked as failed, aborting."
            )
            return

        self._logger.debug(f"Routing parallel subtask {task_context.task_id}.")
        self._route_task(task_context)

        # wait until subtask completes
        self._logger.debug(f"Awaiting parallel subtask {task_context.task_id}.")
        task_context.evt.wait()
        self._logger.debug(f"Parallel subtask {task_context.task_id} has completed.")

        # need this parallel lock to avoid a race condition and not updating parent task
        # as complete or failed.
        with self._parallel_lock:
            if task_context.failed and not parent_task_context.failed:
                self._logger.debug(f"Parallel subtask {task_context.task_id} failed, marking parent as")
                parent_task_context.signal_failed(exception=task_context.exception)  # type: ignore

            if parent_task_context.failed:
                return

            states = [st.completed for st in parent_task_context.subtasks]

            if all(states) and not parent_task_context.completed:
                self._logger.debug(
                    (
                        f"All subtasks of {parent_task_context.task_id} have completed successfully."
                        " Marking as complete"
                    )
                )
                parent_task_context.signal_complete()

    def _handle_device_command_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Handle a device command task.

        This method handles a `DeviceCommandTask`, if there is just one device this sent to a
        :py:class:`DeviceCommandTaskExecutor` via a queue. If ther are multiple devices this is
        converted into a `ParallelTask` with separate `DeviceCommandTask` tasks to be handled,
        which ultimately come back to this method but will then be sent to the `DeviceCommandTaskExecutor`.

        :param task_context: the task context for submitting the `DeviceCommandTask` to
            the `DeviceCommandTaskExecutor`.
        :type task_context: TaskContext
        """
        task = cast(DeviceCommandTask, task_context.task)
        self._logger.debug(f"Received device command task: {task_context}")
        if len(task.devices) == 0:
            # this is a NoOp task and should return immediately
            self._logger.debug(f"Device command task {task_context.task_id} is empty.")
            task_context.signal_complete()
            return
        elif len(task.devices) > 1:
            # run this as a parallel task, this will reenter this method but fall into the else
            self._logger.debug(
                f"Device command task {task_context.task_id} has multiple devices, changing to parallel task."
            )
            parallel_task = ParallelTask(
                subtasks=[
                    DeviceCommandTask(devices=[d], action=task.action, command_name=task.command_name)
                    for d in task.devices
                ]
            )
            child_task_context = TaskContext(
                task=parallel_task,
                parent_task_context=task_context,
            )
            self._handle_parallel_task(child_task_context)
        else:
            # this is a single device so send it to the device command task executor
            child_task_context = DeviceCommandTaskContext(
                task=task,
                device=task.devices[0],
                action=task.action,
                command_name=task.command_name,
                parent_task_context=task_context,
            )
            self._device_command_task_queue.put(child_task_context)

        # wait until child has completed
        self._logger.debug(f"Awaiting for device command task {task_context.task_id} children to complete.")
        child_task_context.evt.wait()

        if child_task_context.failed:
            task_context.signal_failed(exception=child_task_context.exception)  # type: ignore
        else:
            task_context.signal_complete(result=child_task_context.result)

    def _handle_noop_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Handle a no-op task.

        This just calls the signal complete on the task context.
        """
        self._logger.debug(f"Received a NoopTask {task_context}, marking as complete.")
        task_context.signal_complete()

    def _handle_lambda_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Handle a LambdaTask.

        This just calls the action on the task. If successfull it will signal the
        task context as complete.  Errors are allowed to return as this will be
        handled in the `_route_task` method.
        """
        task = cast(LambdaTask, task_context.task)
        self._logger.debug(f"Calling {task}")
        task.action()
        task_context.signal_complete()

    def _route_task(self: TaskExecutor, task_context: TaskContext) -> None:
        """
        Route a task to correct handler method.

        This is an internal method that is used by the background threads to route the tasks to the correct
        handler method.

        :param task_context: the context of the task to run.
        :type task_context: TaskContext
        """
        task = task_context.task

        try:
            route_action = self.task_routing_map[type(task)]
            route_action(task_context)
        except Exception as e:
            self._logger.exception(f"Error in handling task {task_context.task_id}", exc_info=True)
            task_context.signal_failed(e)
