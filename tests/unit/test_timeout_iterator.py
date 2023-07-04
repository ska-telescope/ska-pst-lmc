# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains tests the utility class TimeoutIterator."""

import threading
import time
from datetime import datetime, timedelta
from typing import Generator

import pytest

from ska_pst_lmc.util.timeout_iterator import TimeoutIterator


def test_iterator_should_return_all_items() -> None:
    """Test that all items can be returned from base iterator."""
    items = list(range(10))
    timeout_iter = TimeoutIterator(iter(items))

    output = [i for i in timeout_iter]

    assert output == items


def test_iterator_should_return_all_items_for_slow_iterator() -> None:
    """Test that even a slow iterator can be fully iterated."""
    items = list(range(4))

    def _generator() -> Generator[int, None, None]:
        for i in items:
            yield i
            time.sleep(0.05)

    timeout_iter = TimeoutIterator(
        _generator(),
    )
    output = [i for i in timeout_iter]

    assert output == items


def test_calling_abort_event_stops_iterating(abort_event: threading.Event) -> None:
    """Test that calling abort_event.set() stops the iteration."""
    items = list(range(10))

    def _generator() -> Generator[int, None, None]:
        for i in items:
            yield i
            time.sleep(0.1)

    timeout_iter = TimeoutIterator(
        _generator(),
        abort_event=abort_event,
    )
    assert items[0] == next(timeout_iter)
    abort_event.set()
    time.sleep(0.1)

    with pytest.raises(StopIteration):
        next(timeout_iter)


def test_if_timeout_occured_raise_timeout_error() -> None:
    """Test that if a timeout occurs that iteration stops."""
    items = list(range(10))

    def _generator() -> Generator[int, None, None]:
        for i in items:
            time.sleep(1)
            yield i

    timeout_iter = TimeoutIterator(_generator(), timeout=0.1)
    with pytest.raises(TimeoutError):
        next(timeout_iter)

    with pytest.raises(StopIteration):
        next(timeout_iter)


def test_expected_rate_can_be_used_to_abort_earlier(abort_event: threading.Event) -> None:
    """Test expected rate can be used to abort iteration earlier."""
    items = list(range(10))

    def _generator() -> Generator[int, None, None]:
        for i in items:
            time.sleep(1)
            yield i

    timeout_iter = TimeoutIterator(
        _generator(),
        expected_rate=1000,
        abort_event=abort_event,
    )
    start = datetime.now()
    time.sleep(0.3)
    abort_event.set()

    with pytest.raises(StopIteration):
        next(timeout_iter)

    now = datetime.now()
    diff = now - start
    assert diff < timedelta(milliseconds=400)
