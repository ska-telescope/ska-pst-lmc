# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides a utility class to handle monitoring of disk space."""

from __future__ import annotations

import enum
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable


class MonitoringState(enum.IntEnum):
    """Enum representing monitoring state."""

    WAITING = 0
    STARTING = 1
    MONITORING = 2
    STOPPING = 3
    STOPPED = 4
    SHUTDOWN = 5


class DiskMonitorTask:
    """Class used to monitor disk space."""

    def __init__(
        self: DiskMonitorTask,
        stats_action: Callable[..., None],
        monitoring_polling_rate: int,
        logger: logging.Logger,
    ) -> None:
        """Initialise instance of disk monitor."""
        self._stats_action = stats_action
        self.monitoring_polling_rate = monitoring_polling_rate
        # have 1 more than we need
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._monitoring_condvar = threading.Condition()
        self._monitoring_fut: Future | None = None
        self._stop_monitoring_evt = threading.Event()
        self._state = MonitoringState.WAITING
        self.logger = logger

    def __del__(self: DiskMonitorTask) -> None:
        """Handle deletion of disk monitor."""
        self.shutdown()

    def shutdown(self: DiskMonitorTask) -> None:
        """
        Shutdown disk monitor safely.

        This will first stop monitoring and then shut down the background ThreadPoolExecutor.
        """
        self.logger.debug("Shutting down monitoring task")
        if self._state == MonitoringState.SHUTDOWN:
            self.logger.info("Current monitoring task has already been shutdown.  Exiting")
            return

        try:
            self.stop_monitoring(timeout=2 * self.monitoring_polling_rate / 1000.0)
            self._executor.shutdown(wait=True, cancel_futures=True)

            if self._monitoring_fut is not None:
                self._monitoring_fut.result(timeout=1.0)
            self._set_state(MonitoringState.SHUTDOWN)
        except Exception:
            self.logger.exception("Error in shutting down monitor.", exc_info=True)

    def stop_monitoring(self: DiskMonitorTask, timeout: float | None = None) -> None:
        """Stop monitoring."""
        self.logger.info("Request to stop disk monitoring called.")
        with self._monitoring_condvar:
            if self._state == MonitoringState.WAITING:
                self.logger.warn("Stopping disk monitor task before being started")
                return
            elif self._state == MonitoringState.STOPPED:
                self.logger.info("Stopping disk monitor task that has already stopped.")
                return

            elif self._state == MonitoringState.SHUTDOWN:
                self.logger.warn("Monitoring task already shutdown.")
                return

            elif self._state in [MonitoringState.STARTING, MonitoringState.MONITORING]:
                self._stop_monitoring_evt.set()
                self._set_state(MonitoringState.STOPPING)
            else:
                self.logger.debug("Already Stopping disk monitoring task.")

        with self._monitoring_condvar:
            self._monitoring_condvar.wait_for(
                predicate=lambda: self._state == MonitoringState.STOPPED,
                timeout=timeout,
            )

        # wait for future result
        try:
            if self._monitoring_fut is not None:
                self._monitoring_fut.result(timeout=1.0)
        except Exception:
            self.logger.exception("Error in waiting for result of monitoring background task.", exc_info=True)

    def start_monitoring(self: DiskMonitorTask) -> None:
        """
        Start monitoring of disk.

        This will launch a background process that periodically polls the API to get the current disk stats.
        """
        self.logger.info(f"Starting disk monitoring. Polling rate is {self.monitoring_polling_rate}ms")
        with self._monitoring_condvar:
            if self._state in [MonitoringState.WAITING, MonitoringState.STOPPED]:
                self.logger.debug(f"Starting monitoring of disk.  Current state is {self._state}")

            elif self._state == MonitoringState.STOPPING:
                # currently stopping. Wait for the stop process to finish
                self._monitoring_condvar.wait_for(predicate=lambda: self._state == MonitoringState.STOPPED)
            elif self._state == MonitoringState.SHUTDOWN:
                self.logger.warn("Monitoring task has already been shutdown.  Can't restart.")
                raise RuntimeError("Monitoring task has already been shutdown.  Can't restart.")
            else:
                self.logger.warn("Monitoring disk space already.")
                return

            self._set_state(MonitoringState.STARTING)

        self.logger.debug("Submitting background monitoring task to executor")
        self._monitoring_fut = self._executor.submit(self._monitor_background)

        with self._monitoring_condvar:
            self._monitoring_condvar.wait_for(predicate=lambda: self._state != MonitoringState.STARTING)

    def _set_state(self: DiskMonitorTask, state: MonitoringState) -> None:
        """Set the monitoring state and notify any threads waiting on condition."""
        self._state = state
        with self._monitoring_condvar:
            self._monitoring_condvar.notify_all()

    def _monitor_background(self: DiskMonitorTask) -> None:
        """
        Run monitoring in background.

        This should have been launched be the ThreadPoolExecutor rather than being called directly.
        """

        def _should_stop_monitoring() -> bool:
            return self._stop_monitoring_evt.is_set() or self._state != MonitoringState.MONITORING

        try:
            self.logger.debug("Background monitoring task has started.")
            self._set_state(MonitoringState.MONITORING)

            while not _should_stop_monitoring():
                with self._monitoring_condvar:
                    if self._monitoring_condvar.wait_for(
                        predicate=lambda: _should_stop_monitoring(),
                        timeout=self.monitoring_polling_rate / 1000.0,
                    ):
                        self.logger.info("Monitoring background task received stop condition. Exiting.")
                        break

                self._stats_action()
        except Exception:
            self.logger.exception("Error in background processing of monitor task.", exc_info=True)
        finally:
            self.logger.info(
                "In finally of _monitor_background. Marking state as STOPPED and notifying wait conditions."
            )
            self._set_state(MonitoringState.STOPPED)

            self.logger.info("Disk monitoring task has stopped.")
