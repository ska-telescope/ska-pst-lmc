# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This is used to wrap an iterator with a timeout."""

from __future__ import annotations

import logging
import threading
from queue import Empty, Queue
from threading import Event, Thread
from typing import Iterable, Iterator, Optional, TypeVar, Union

T = TypeVar("T")

NO_TIMEOUT = 0.0


class TimeoutIterator(Iterable[T]):
    """
    An iterator that can timeout.

    The implementation of this uses a background thread to get the items and put them on a queue, while the
    next functionality of this will block
    """

    def __init__(
        self: TimeoutIterator,
        iterator: Iterator[T],
        abort_event: Optional[Event] = None,
        timeout: float = NO_TIMEOUT,
        expected_rate: float = 0.0,
    ) -> None:
        """Initialise iterator."""
        self._iterator = iterator
        self._timeout = timeout
        self._queue: Queue[Union[T, BaseException]] = Queue()
        self._done = False
        self._abort_event = abort_event or threading.Event()
        self._expected_rate = expected_rate
        self._logger = logging.getLogger(__name__)
        self._first = True

        self._thread = Thread(target=self.__background_iterate, daemon=True)
        self._thread.start()

    def __del__(self: TimeoutIterator) -> None:
        """
        Tear down iterator.

        This makes sure that the background thread is notified to abort.
        """
        self._abort_event.set()

    def __iter__(self: TimeoutIterator) -> Iterator[T]:
        """Return self as an iterator."""
        return self

    def __next__(self: TimeoutIterator) -> T:
        """Return the next item."""
        if self._done or self._abort_event.is_set():
            raise StopIteration

        # cannot guarantee that the iterator has produced anything yet
        # wait for the expected rate on first call.
        if self._first:
            import time

            time.sleep(self._expected_rate)
            self._first = False

        try:
            if self._timeout == NO_TIMEOUT:
                data = self._queue.get()
            else:
                self._logger.debug(f"Waiting {self._timeout} secs for item data.")
                data = self._queue.get(timeout=self._timeout)

            self._queue.task_done()
        except Empty:
            self._logger.debug(
                f"Received Empty. Queue size is {self._queue.qsize()}. Queue object is {self._queue}"
            )

            self._done = True

            if self._abort_event.is_set():
                raise StopIteration

            self._timedout = True
            raise TimeoutError

        if isinstance(data, BaseException):
            if isinstance(data, StopIteration):
                self._done = True
            raise data

        return data

    def __background_iterate(self: TimeoutIterator) -> None:
        """Iterate over items in the background."""
        try:
            while True:
                if self._expected_rate > 0.0:
                    # this allows us not having to wait a full
                    # rate to get told to stop as the iterator
                    # will still block, but when the event is set
                    # it will notify this thread and it will stop
                    # blocking.
                    if self._abort_event.wait(timeout=self._expected_rate):
                        raise StopIteration
                else:
                    if self._abort_event.is_set():
                        raise StopIteration

                item = next(self._iterator)
                self._queue.put_nowait(item)

        except BaseException as e:
            if not isinstance(e, StopIteration):
                self._logger.warning("Exception raised in background processing.", exc_info=True)
            self._queue.put(e)
