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
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple, Union, cast

from ska_tango_base.base.base_device import DevVarLongStringArrayType

from ska_pst_lmc.device_proxy import ChangeEventSubscription, PstDeviceProxy

from .callback import Callback

_logger = logging.getLogger(__name__)

__all__ = ["DeviceAction", "Job", "SequentialJob", "ParallelJob", "DeviceCommandJob", "submit_job"]

DeviceAction = Callable[[PstDeviceProxy], DevVarLongStringArrayType]
"""A type alias representing a callable of a long running command on a device proxy."""

JOB_QUEUE: queue.Queue = queue.Queue()
"""A global queue used for submitting jobs contexts.

This should not be used directly but via the :py:class:`JobExecutor`.
"""

DEVICE_COMMAND_JOB_QUEUE: queue.Queue = queue.Queue()
"""A global queue used for submitting :py:class:`DeviceCommandJob` jobs.

This queue is shared between the :py:class:`JobExecutor` and the
:py:class:`DeviceCommandJobExecutor`. This should not be used directly.
"""


@dataclass
class SequentialJob:
    """A class used to handle sequential jobs.

    Instances of this class take a list of jobs that will all
    be run in sequentially. This job is not complete until the
    last job is complete.

    :ivar tasks: a list of subtasks/jobs to be performed sequentially
    :type tasks: List[Job]
    """

    tasks: List[Job]


@dataclass
class ParallelJob:
    """A class used to handle jobs that can be run in parallel.

    Instances of this class take a list of jobs that can be all
    run in parallel. This job is not complete until all the jobs
    are complete.

    :ivar tasks: a list of subtasks/jobs to be performed concurrently
    :type tasks: List[Job]
    """

    tasks: List[Job]


@dataclass
class DeviceCommandJob:
    """A class used to handle a command to be executed on remote devices.

    Instances of this class take a list of devices and an action to
    be performed on a remote device. If more than one device is used this
    is converted into a :py:class:`ParallelJob` that separate instances
    of this class, one per device.  This job is not complete until all
    the remote devices have completed the action.

    Commands are sent to the DeviceCommandExecutor to allow to be tracked
    by listening to events on the `longRunningCommandResult` property.

    :ivar devices: list of devices to perform action upon.
    :type devices: List[PstDeviceProxy]
    :ivar action: the callbable to perform on each device proxy.
    :type action: Callable[[PstDeviceProxy], DevVarLongStringArrayType]
    """

    devices: List[PstDeviceProxy]
    action: DeviceAction = field(repr=False)
    command_name: str


Job = Union[SequentialJob, ParallelJob, DeviceCommandJob]


@dataclass
class JobContext:
    """A data class representing a job and the callback to use when complete.

    :ivar job: the job the needs to be executed.
    :ivar callback: the optional callback to use when job is complete, default is None.
    """

    job: Job
    callback: Callback = None

    def __repr__(self: JobContext) -> str:
        """Create a string representation of JobContext.

        :return: a string representation of a JobContext
        :rtype: str
        """
        return f"JobContext(job='{self.job}')"


@dataclass
class _ParallelJobContext:
    """A data class representiong the job context for a `ParallelJob`.

    :ivar job_id: a UUID string representing the job.
    :ivar task_signals: a list of :py:class:`threading.Event` used to track the state of
        the subtasks. There is one signal per subtask.
    :ivar signal: the signal used to notify the whole job is complete, which in turn can
        then call the job's associated callback.
    """

    job_id: str
    tasks_signals: List[threading.Event] = field(repr=False)
    signal: threading.Event = field(repr=False)


@dataclass
class _ParallelJobTaskContext:
    """A data class representing the job context of a subtask for a `ParallelJob`.

    :ivar job_id: a UUID string representing the job.
    :ivar task_id: a UUID string representing the subtask.
    :ivar job: the job the subtask is to perform, this maybe a `SequentialJob`, a
        `DeviceCommandJob` or even another `ParallelJob`.
    :ivar signal: the signal used to notify the subtask is complete. This signal is
        also stored in the `task_signals` field of a `_ParallelJobContext`.
    """

    job_id: str
    task_id: str
    job: Job
    signal: threading.Event = field(repr=False)


@dataclass
class DeviceCommandJobContext:
    """A data class representing the job context of a `DeviceCommandJob`.

    :ivar device: the device that the action is to be performed against.
    :ivar action: the action to perform on the device proxy.
    :ivar signal: the signal used to notify the command is complete. Since
        device commands run in the background on a remote device, this signal
        is used to notify the executor that this remote job is complete.
    """

    device: PstDeviceProxy
    command_name: str
    action: DeviceAction = field(repr=False)
    signal: threading.Event = field(repr=False)


class DeviceCommandJobExecutor:
    """Class to handle executing and tracking commands on device proxies.

    This class uses a queue to receive job commands, while a background
    thread receives these messages and then executes the commands.

    Since the remote commands also run in the background on the device, this
    class needs to subscribe to the `longRunningCommandResult` property
    and listen to events of when this changes for a given command.
    This class was created to allow the normal `JobExecutor` not having
    to worry about all the necessary subscription and event handling.

    Clients should submit `DeviceCommandJob` jobs to the `JobExecutor` rather
    than building up a `DeviceCommandJobContext` and sending it to the
    job queue.

    Instances of class and the `JobExecutor` class work together by sharing
    a queue, the default is `DEVICE_COMMAND_JOB_QUEUE`. If creating separate
    instances of both classes, make sure that queue between them is the same.
    """

    def __init__(
        self: DeviceCommandJobExecutor,
        job_queue: queue.Queue = DEVICE_COMMAND_JOB_QUEUE,
    ) -> None:
        """Initialise the executor.

        :param job_queue: the queue used to submit jobs to,
            defaults to DEVICE_COMMAND_JOB_QUEUE. This should be
            shared by the `JobExecutor` which is the producer of the messages
            this class consumes.
        :type job_queue: queue.Queue, optional
        """
        self._job_queue = job_queue
        self._job_context_map: Dict[str, DeviceCommandJobContext] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self._result_subscriptions: Dict[PstDeviceProxy, ChangeEventSubscription] = {}

        self._running = False

    def __del__(self: DeviceCommandJobExecutor) -> None:
        """Tear down class being destroyed."""
        self.stop()

    def __enter__(self: DeviceCommandJobExecutor) -> DeviceCommandJobExecutor:
        """Context manager start."""
        self.start()
        return self

    def __exit__(self: DeviceCommandJobExecutor, exc_type: None, exc_val: None, exc_tb: None) -> None:
        """Context manager exit."""
        self.stop()

    def stop(self: DeviceCommandJobExecutor) -> None:
        """Stop the executor."""
        if self._running:
            self._running = False
            self._stop.set()
            self._tpe.shutdown()
            for subscription in self._result_subscriptions.values():
                subscription.unsubscribe()

    def start(self: DeviceCommandJobExecutor) -> None:
        """Start the executor."""
        self._running = True
        # need to reset this each time we start.
        self._stop = threading.Event()
        self._tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="DeviceCommanJobThread"
        )
        self._tpe.submit(self._process_queue)

    def _ensure_subscription(self: DeviceCommandJobExecutor, device: PstDeviceProxy) -> None:
        """Ensure there is a change event subscription for `longRunningCommandResult` for device.

        :param device: the device to make sure that there is a subscription against.
        :type device: PstDeviceProxy
        """
        if device not in self._result_subscriptions:
            self._result_subscriptions[device] = device.subscribe_change_event(
                "longrunningcommandresult", self._handle_subscription_event
            )

    def _process_queue(self: DeviceCommandJobExecutor) -> None:
        """Process messages off job queue.

        This method uses an infinite loop to read messages off the
        job queue. Once a message is received it will call the
        `_handle_job` method.

        The loop is only stopped when instances of this class are
        destroyed.
        """
        try:
            while not self._stop.is_set():
                try:
                    job_context = cast(DeviceCommandJobContext, self._job_queue.get(timeout=0.1))
                    _logger.debug(f"DeviceCommandJobExecutor received a device job: {job_context}")
                    self._handle_job(job_context)
                except queue.Empty:
                    continue
        except Exception:
            _logger.exception("Error processing device command queue", exc_info=True)

    def _handle_job(self: DeviceCommandJobExecutor, job_context: DeviceCommandJobContext) -> None:
        """Handle job request that has been received.

        This will ensure that the device has a subscription to the `longRunningCommandResult`
        property on the device. After that it will execute the action and recording the `command_id`
        in an internal map that can be then used to later signal that a job has completed.
        """
        # ensure subscription
        device = job_context.device
        action = job_context.action

        self._ensure_subscription(device)

        with self._lock:
            (_, [command_id]) = action(device)
            if command_id:
                self._job_context_map[command_id] = job_context

    def _handle_subscription_event(self: DeviceCommandJobExecutor, event: Tuple[str, str]) -> None:
        """Handle a subscription event.

        For the `longRunningCommandResult` this returns a tuple of `(command_id, msg)`. The `command_id`
        is used by this method to see if there is a job that needs to be notified that it has completed.

        :param event: the event details, which is a tuple of `(command_id, msg)`
        :type event: Tuple[str, str]
        """
        # this will come from the subscription
        (command_id, _) = event
        _logger.debug(f"Received a subscription event for command {command_id}")
        with self._lock:
            if command_id in self._job_context_map:
                self._job_context_map[command_id].signal.set()
                del self._job_context_map[command_id]


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
        self._parallel_job_queue: queue.Queue[_ParallelJobTaskContext] = queue.Queue()
        self._parallel_job_context_map: Dict[str, _ParallelJobContext] = {}

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

        if callback:
            callback()

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
            _ParallelJobTaskContext(job_id=job_id, task_id=str(uuid.uuid4()), signal=threading.Event(), job=t)
            for t in job.tasks
        ]

        job_context = _ParallelJobContext(
            job_id=job_id, tasks_signals=[tc.signal for tc in task_contexts], signal=threading.Event()
        )

        with self._parallel_lock:
            self._parallel_job_context_map[job_id] = job_context
            for tc in task_contexts:
                self._parallel_job_queue.put(tc)

        job_context.signal.wait()
        if callback:
            callback()

    def _handle_parallel_task(self: JobExecutor, task_context: _ParallelJobTaskContext) -> None:
        """Handle a parallel job subtask.

        This converts the `task_context` into a `JobContext` and calls the :py:meth:`_handle_job`
        method to be processed, this doesn't happen on the main thread so it won't block.

        :param task_context: the subtask context
        :type task_context: _ParallelJobTaskContext
        """
        job_context = JobContext(job=task_context.job, callback=task_context.signal.set)

        self._handle_job(job_context)
        task_context.signal.wait()
        self._handle_task_complete(task_context)

    def _handle_task_complete(self: JobExecutor, task_context: _ParallelJobTaskContext) -> None:
        """Handle parallel task being complete.

        :param task_context: the task context of the completed task.
        :type task_context: _ParallelJobTaskContext
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
            if callback:
                callback()
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

DEVICE_COMMAND_JOB_EXECUTOR: DeviceCommandJobExecutor = DeviceCommandJobExecutor()
"""Global :py:class:`DeviceCommandJobExecutor`.

Using this means alongside the global `JobExecutor` means that the two executors
are using the shared queue.
"""


def submit_job(job: Job, callback: Callback = None) -> None:
    """Submit a job to the global `JobExecutor`.

    :param job: the job to submit.
    :type job: Job
    :param callback: callback to use when job completes, defaults to None
    :type callback: Callback, optional
    """
    # ensure the executors are running, there is an atexit
    # to ensure they are stopped.
    JOB_EXECUTOR.start()
    DEVICE_COMMAND_JOB_EXECUTOR.start()

    JOB_EXECUTOR.submit_job(job=job, callback=callback)


atexit.register(DEVICE_COMMAND_JOB_EXECUTOR.stop)
atexit.register(JOB_EXECUTOR.stop)
