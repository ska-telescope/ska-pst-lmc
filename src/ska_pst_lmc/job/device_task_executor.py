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
from typing import Dict, Tuple, cast

from ska_pst_lmc.device_proxy import ChangeEventSubscription, PstDeviceProxy

from .common import DEVICE_COMMAND_JOB_QUEUE
from .context import DeviceCommandTaskContext

_logger = logging.getLogger(__name__)


class DeviceCommandTaskExecutor:
    """Class to handle executing and tracking commands on device proxies.

    This class uses a queue to receive job commands, while a background
    thread receives these messages and then executes the commands.

    Since the remote commands also run in the background on the device, this
    class needs to subscribe to the `longRunningCommandResult` property
    and listen to events of when this changes for a given command.
    This class was created to allow the normal `JobExecutor` not having
    to worry about all the necessary subscription and event handling.

    Clients should submit `DeviceCommandJob` jobs to the `JobExecutor` rather
    than building up a `DeviceCommandTaskContext` and sending it to the
    job queue.

    Instances of class and the `JobExecutor` class work together by sharing
    a queue, the default is `DEVICE_COMMAND_JOB_QUEUE`. If creating separate
    instances of both classes, make sure that queue between them is the same.
    """

    def __init__(
        self: DeviceCommandTaskExecutor,
        task_queue: queue.Queue = DEVICE_COMMAND_JOB_QUEUE,
    ) -> None:
        """Initialise the executor.

        :param task_queue: the queue used to submit jobs to,
            defaults to DEVICE_COMMAND_JOB_QUEUE. This should be
            shared by the `JobExecutor` which is the producer of the messages
            this class consumes.
        :type task_queue: queue.Queue, optional
        """
        self._task_queue = task_queue
        self._task_context_map: Dict[str, DeviceCommandTaskContext] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self._result_subscriptions: Dict[PstDeviceProxy, ChangeEventSubscription] = {}

        self._running = False

    def __del__(self: DeviceCommandTaskExecutor) -> None:
        """Tear down class being destroyed."""
        self.stop()

    def __enter__(self: DeviceCommandTaskExecutor) -> DeviceCommandTaskExecutor:
        """Context manager start."""
        self.start()
        return self

    def __exit__(self: DeviceCommandTaskExecutor, exc_type: None, exc_val: None, exc_tb: None) -> None:
        """Context manager exit."""
        self.stop()

    def stop(self: DeviceCommandTaskExecutor) -> None:
        """Stop the executor."""
        if self._running:
            self._running = False
            self._stop.set()
            self._tpe.shutdown()
            for subscription in self._result_subscriptions.values():
                subscription.unsubscribe()

    def start(self: DeviceCommandTaskExecutor) -> None:
        """Start the executor."""
        self._running = True
        # need to reset this each time we start.
        self._stop = threading.Event()
        self._tpe = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="DeviceCommanJobThread"
        )
        self._tpe.submit(self._process_queue)

    def _ensure_subscription(self: DeviceCommandTaskExecutor, device: PstDeviceProxy) -> None:
        """Ensure there is a change event subscription for `longRunningCommandResult` for device.

        :param device: the device to make sure that there is a subscription against.
        :type device: PstDeviceProxy
        """
        if device not in self._result_subscriptions:
            self._result_subscriptions[device] = device.subscribe_change_event(
                "longrunningcommandresult", self._handle_subscription_event
            )

    def _process_queue(self: DeviceCommandTaskExecutor) -> None:
        """Process messages off job queue.

        This method uses an infinite loop to read messages off the
        job queue. Once a message is received it will call the
        `_handle_job` method.

        The loop is only stopped when instances of this class are
        destroyed.
        """
        while not self._stop.is_set():
            try:
                task_context = cast(DeviceCommandTaskContext, self._task_queue.get(timeout=0.1))
                _logger.debug(f"DeviceCommandTaskExecutor received a device job: {task_context}")
                self._handle_task(task_context)
            except queue.Empty:
                continue

    def _handle_task(self: DeviceCommandTaskExecutor, task_context: DeviceCommandTaskContext) -> None:
        """Handle task request that has been received.

        This will ensure that the device has a subscription to the `longRunningCommandResult`
        property on the device. After that it will execute the action and recording the `command_id`
        in an internal map that can be then used to later signal that a job has completed.
        """
        # ensure subscription
        device = task_context.device
        action = task_context.action

        self._ensure_subscription(device)

        with self._lock:
            try:
                # TODO - handle result code is not QUEUED
                (_, [command_id]) = action(device)
                if command_id:
                    self._task_context_map[command_id] = task_context
            except Exception as e:
                _logger.exception(
                    f"Error while excuting command '{device}.{task_context.command_name}()'", exc_info=True
                )
                task_context.signal_failed(e)

    def _handle_subscription_event(self: DeviceCommandTaskExecutor, event: Tuple[str, str]) -> None:
        """Handle a subscription event.

        For the `longRunningCommandResult` this returns a tuple of `(command_id, msg)`. The `command_id`
        is used by this method to see if there is a job that needs to be notified that it has completed.

        :param event: the event details, which is a tuple of `(command_id, msg)`
        :type event: Tuple[str, str]
        """
        import json

        # this will come from the subscription
        (command_id, result) = event
        _logger.debug(f"Received a subscription event for command {command_id} with msg: '{result}'")
        with self._lock:
            if command_id in self._task_context_map:
                task_context = self._task_context_map[command_id]

                try:
                    task_context.signal_complete(result=json.loads(result))
                except json.JSONDecodeError:
                    task_context.signal_failed_from_str(msg=result)

                del self._task_context_map[command_id]


DEVICE_COMMAND_TASK_EXECUTOR: DeviceCommandTaskExecutor = DeviceCommandTaskExecutor()
"""Global :py:class:`DeviceCommandTaskExecutor`.

Using this means alongside the global `JobExecutor` means that the two executors
are using the shared queue.
"""

atexit.register(DEVICE_COMMAND_TASK_EXECUTOR.stop)
