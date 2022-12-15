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
from .context import DeviceCommandJobContext

_logger = logging.getLogger(__name__)


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


DEVICE_COMMAND_JOB_EXECUTOR: DeviceCommandJobExecutor = DeviceCommandJobExecutor()
"""Global :py:class:`DeviceCommandJobExecutor`.

Using this means alongside the global `JobExecutor` means that the two executors
are using the shared queue.
"""

atexit.register(DEVICE_COMMAND_JOB_EXECUTOR.stop)
