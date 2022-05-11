# -*- coding: utf-8 -*-
#
# This file is part of the PstBeam project
#
# Swinburne University of Technology
#
# Distributed under the terms of the none license.
# See LICENSE.txt for more info.

"""This module is to abstract background task processes."""

from __future__ import annotations

import functools
import logging
from enum import IntEnum
from logging import Logger
from threading import Thread
from typing import Any, Callable, List, Optional, TypeVar, cast

from readerwriterlock import rwlock

__all__ = [
    "BackgroundTaskProcessor",
    "BackgroundTask",
    "background_task",
    "RunState",
]

Wrapped = TypeVar("Wrapped", bound=Callable[..., Any])


def background_task(func: Wrapped) -> Wrapped:
    """
    Return a decorated function that runs tasks in a background.

    Use this decorator on methods of a class that contains
    a :py:class:`BackgroundTaskProcessor` in the field
    `_background_task_processor`. If the field doesn't exist
    than this wrapper will error with the field not existing.

    .. code-block:: python

        @background_task
        def assign_resources(self):
            ...

    :param func: the wrapped function

    :return: the wrapped function
    """

    @functools.wraps(func)
    def _wrapper(
        obj: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        def _task() -> None:
            func(obj, *args, **kwargs)

        obj._background_task_processor.submit_task(_task)

    return cast(Wrapped, _wrapper)


class BackgroundTaskProcessor:
    """Class used for submitting and reaping of background tasks.

    This class is used to abstract away needing to hold and monitor
    :py:class:`BackgrounTask` objects. This class submits a background
    task itself to reap completed tasks.
    """

    def __init__(self: BackgroundTaskProcessor, default_logger: logging.Logger):
        """Initialise processor.

        :param default_logger: the logger that the tasks should use if
            one is not provided.
        :type default_logger: logging.Logger
        """
        # need a queue
        self._tasks: List[BackgroundTask] = list()
        self._default_logger: logging.Logger = default_logger

        # need a background reaper
        self._reaper = BackgroundTask(
            action_fn=self._reap,
            logger=self._default_logger,
            frequency=10.0,
        )
        self._reaper.run()

    def __del__(self: BackgroundTaskProcessor) -> None:
        """Destructor for processor.

        Stops all the background tasks.
        """
        for t in self._tasks:
            t.stop()
        self._reaper.stop()

    def submit_task(
        self: BackgroundTaskProcessor,
        action_fn: Callable,
        logger: Optional[logging.Logger] = None,
        frequency: Optional[float] = None,
    ) -> BackgroundTask:
        """Submit a background task to run.

        This will submit a background task, whether it is a one
        shot task or a periodic task. It can take an optional
        logger, or the default logger used by the processor is used,
        and an optional frequency.

        :param task: the callable function to run, this must wrap
            its own callbacks if needed.
        :param logger: an optional logger to use, else the default logger
            is used.
        :param frequency: an optional parameter for background task to
            run at a given frequency.
        :returns: the task that was submit if there is a need for
            external monitoring.
        :rtype: BackgroundTask
        """
        task: BackgroundTask = BackgroundTask(
            action_fn=action_fn,
            logger=logger or self._default_logger,
            frequency=frequency,
        )
        self._tasks.append(task)
        task.run()

        return task

    def _reap(self: BackgroundTaskProcessor) -> None:
        """Reap completed tasks."""
        for t in self._tasks:
            if not t.running():
                self._tasks.remove(t)


class RunState(IntEnum):
    """Enum to represent run state of :py:class:`BackgroundTask`."""

    STOPPED = (1,)
    """Background task is stopped and not running.

    This is the default state when the task is created.
    """
    STARTING = (2,)
    """The state the task is put into when the task is started.

    This is an intermediate state. When the method :meth:`BackgroundTask.run`
    is called the task goes into a STARTING state. If the task starts successfully
    then the state goes into RUNNING.
    """

    RUNNING = (3,)
    """The state to indicate that the task is running.

    This state represents that the task is running successfully.
    """

    STOPPING = (4,)
    """The state the task is put into when asked to stop.

    This is an intermediate state, used to avoid calling stop mulitple times.
    When the method :meth:`BackgroundTask.stop` is called the task will
    go in to the STOPPING state.
    """

    ERRORED = (5,)
    """The state to represent that the task has errored.

    The task can go into this state while starting, running or stopping.
    """

    def running(self: RunState) -> bool:
        """Check if in a state that represents a running state.

        If the state is STARTING or RUNNING then this is considered as
        running state.

        :returns: is in a running state
        """
        return self in [RunState.STARTING, RunState.RUNNING]

    def errored(self: RunState) -> bool:
        """Check if in an errored state.

        This only happens if the state is ERRORED.

        :returns: is in a errored state
        """
        return self == RunState.ERRORED


class BackgroundTask:
    """BackgroundTask.

    This class is used for background task processing. Rather
    than code being littered with creating background threads
    or asyncio code, this class is used to provide the functionality
    to start/stop the process.

    The task has to be explicitly started. However, if this task
    is deleted by the Python runtime it will stop the background
    processing. It is, however, advised to that a user explicitly
    stops the task.

    This task does waiting/looping and the provided action is
    not expected to do any waiting.
    """

    _state: RunState = RunState.STOPPED
    _thread: Optional[Thread] = None
    _exception: Optional[Exception] = None
    _completed: bool = False

    def __init__(
        self,
        action_fn: Callable[[], None],
        logger: Logger,
        frequency: Optional[float] = None,
        daemon: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialise background task.

        :param action_fn: action to call during background process. If
            the frequency is set then this is a per loop callback, else
            this action will be called once.
        :param logger: logger to be used by the task object.
        :param frequency: how often to execute the action. If None (the default)
            then action is only called once, else this task will attempt
            to sleep for 1/frequency seconds.
        :param daemon: run task in a background daemone thread (default is True)
        """
        self._action_fn = action_fn
        self._logger = logger
        self._frequency = frequency
        self._daemon = daemon
        self._lock = rwlock.RWLockWrite()

    def __del__(self: BackgroundTask) -> None:
        """Deconstruct object.

        Stops any background thread if processing.
        """
        if self.running():
            self.stop()
        else:
            self._join()

    def _set_state(self: BackgroundTask, state: RunState) -> None:
        """Set run state of background task.

        :param state: state to set task to.
        """
        with self._lock.gen_wlock():
            self._state = state

    def _run(self: BackgroundTask) -> None:
        """Background thread action."""
        self._set_state(RunState.RUNNING)
        try:
            while self.running():
                self._action_fn()
                if self._frequency:
                    import time

                    time.sleep(1 / self._frequency)
                else:
                    self._set_state(RunState.STOPPED)
                    self._completed = True
                    self._thread = None
                    return
        except Exception as e:
            self._logger.error("Error during processing of task.", exc_info=True)
            self._set_state(RunState.ERRORED)
            self._exception = e
            self._completed = True
            self._thread = None

    def run(self: BackgroundTask) -> None:
        """Run the background task.

        If the task is already in a running state then this task will exit
        immediately.
        """
        assert not self._completed, "Task has already completed, cannot run it again."

        if self.running():
            return

        with self._lock.gen_wlock():
            self._state = RunState.STARTING

        self._thread = Thread(target=self._run, daemon=self._daemon)
        self._thread.start()

    def running(self: BackgroundTask) -> bool:
        """Check if the task is in a running state."""
        if self._thread is None:
            return False

        with self._lock.gen_rlock():
            return self._state.running()

    def has_errored(self: BackgroundTask) -> bool:
        """Check if the task has errored."""
        with self._lock.gen_rlock():
            return self._state.errored()

    def exception(self: BackgroundTask) -> Optional[Exception]:
        """Return the exception raised during background processing.

        If no exception has been raised then None is returned.

        :returns: the exception raised during background processing.
        """
        return self._exception

    def _join(self: BackgroundTask) -> None:
        """Wait for background task to end and join."""
        if self._thread is None:
            return

        try:
            self._thread.join()

            with self._lock.gen_rlock():
                if self._state.errored():
                    return

            self._set_state(RunState.STOPPED)
        except Exception as e:
            self._logger.warn("Waiting for background thread raised error.", e)
            self._set_state(RunState.ERRORED)
            self._exception = e
        finally:
            self._completed = True
            self._thread = None

    def stop(self: BackgroundTask) -> None:
        """Stop the background task.

        If the task is not in a running state this will exit immediately.
        """
        with self._lock.gen_wlock():
            # have a write lock which implies we can read the state.
            if not self._state.running():
                return

            self._state = RunState.STOPPING

        self._join()
