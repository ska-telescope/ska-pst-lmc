# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module is used in testing for tracking the states of long running commands (LRC)."""

from __future__ import annotations

__all__ = ["LongRunningCommandTracker"]

import logging
import threading
from typing import Dict, List

import tango
from readerwriterlock import rwlock
from ska_tango_base.executor import TaskStatus


class LongRunningCommandTracker:
    """A convinence class used to help check a Tango Device command.

    This class can be used to check that a command executed on a
    :py:class:`DeviceProxy` fires the correct change events
    for task status, the completion state, and any changes through
    the :py:class:`ObsState`.
    """

    def __init__(
        self: LongRunningCommandTracker,
        device: tango.DeviceProxy,
        logger: logging.Logger,
    ) -> None:
        """Initialise command checker."""
        self._device = device
        self._lock = rwlock.RWLockWrite()
        self._command_status_events: Dict[str, List[TaskStatus]] = {}
        self._logger = logger
        self._condvar = threading.Condition()
        self.subscription_id = self._device.subscribe_event(
            "longRunningCommandStatus",
            tango.EventType.CHANGE_EVENT,
            self._handle_evt,
        )

    def _handle_evt(self: LongRunningCommandTracker, event: tango.EventData) -> None:
        try:
            self._logger.debug(f"Received event for longRunningCommandStatus, event = {event}")
            if event.err:
                self._logger.warning(f"Received failed change event: error stack is {event.errors}.")
                return
            elif event.attr_value is None:
                warning_message = (
                    "Received change event with empty value. Falling back to manual "
                    f"attribute read. Event.err is {event.err}. Event.errors is\n"
                    f"{event.errors}."
                )
                self._logger.warning(warning_message)
                value = self._device.longRunningCommandStatus
            else:
                value = event.attr_value

            if isinstance(value, tango.DeviceAttribute):
                value = value.value

            if value is None:
                return

            self._logger.debug(
                f"Received event callback for {self._device}.longRunningCommandStatus with value: {value}"
            )

            # LRC command value is a tuple in the form of (command1_id, status_1, command2_id, status_2, ...)
            # this converts a tuple to a dictionary
            value = list(value)
            values: Dict[str, TaskStatus] = {
                value[i]: TaskStatus[value[i + 1]] for i in range(0, len(value), 2)
            }

            with self._lock.gen_wlock():
                for command_id, status in values.items():
                    if command_id not in self._command_status_events:
                        self._command_status_events[command_id] = list()

                    curr_command_status_events = self._command_status_events[command_id]
                    # add status to previous states if
                    if len(curr_command_status_events) == 0 or curr_command_status_events[-1] != status:
                        curr_command_status_events.append(status)

                with self._condvar:
                    self._condvar.notify_all()
        except Exception:
            self._logger.exception("Error in handling of event", exc_info=True)

    def assert_command_status_events(
        self: LongRunningCommandTracker,
        command_id: str,
        expected_command_status_events: List[TaskStatus] = [
            TaskStatus.QUEUED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
        ],
    ) -> None:
        """Assert that the command has the correct status events.

        :param command_id: the id of the command to assert events against.
        :param expected_command_status_events: a list of expected
            status events of the command, these should be in the
            order the events happen. Default expected events are:
            [TaskStatus.QUEUED, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        """
        with self._lock.gen_rlock():
            assert (
                command_id in self._command_status_events
            ), f"Expected command status events for command {command_id}"
            assert expected_command_status_events == self._command_status_events[command_id], (
                f"Expected command status events to be {expected_command_status_events} "
                f"but received {self._command_status_events[command_id]}"
            )

    def wait_for_command_to_complete(
        self: LongRunningCommandTracker, command_id: str, timeout: float = 5.0
    ) -> None:
        """Wait for a command to complete.

        This waits for the a given command to complete within a given timeout.
        A command is considered complete if the last status event is either:
        TaskStatus.COMPLETED, TaskStatus.ABORTED, TaskStatus.FAILED, or
        TaskStatus.REJECTED.

        :param command_id: the id of the command to assert events against.
        """

        def _command_complete() -> bool:
            with self._lock.gen_rlock():
                if command_id not in self._command_status_events:
                    return False

                curr_status_events = self._command_status_events[command_id]
                if len(curr_status_events) == 0:
                    return False

                return curr_status_events[-1] in [
                    TaskStatus.COMPLETED,
                    TaskStatus.ABORTED,
                    TaskStatus.FAILED,
                    TaskStatus.REJECTED,
                ]

        with self._condvar:
            result = self._condvar.wait_for(_command_complete, timeout=timeout)
            if result:
                return

            raise TimeoutError(f"Expected command {command_id} to complete in {timeout:.1f}s")
