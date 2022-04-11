"""This module defines elements of the pytest test harness shared by all tests."""
from __future__ import annotations

import collections
import logging
import time
from typing import Any, Generator

import pytest
import tango
from ska_tango_base.testing.mock import MockCallable, MockChangeEventCallback
from tango import DeviceProxy
from tango.test_context import DeviceTestContext


@pytest.fixture(scope="class")
def device_properties() -> dict:
    """
    Fixture that returns device_properties to be provided to the device under test.

    This is a default implementation that provides no properties.

    :return: properties of the device under test
    """
    return {}


@pytest.fixture()
def tango_context(device_test_config: dict) -> Generator[DeviceTestContext, None, None]:
    """Return a Tango test context object, in which the device under test is running."""
    component_manager_patch = device_test_config.pop("component_manager_patch", None)
    if component_manager_patch is not None:
        device_test_config["device"].create_component_manager = component_manager_patch

    tango_context = DeviceTestContext(**device_test_config)
    tango_context.start()
    yield tango_context
    tango_context.stop()


@pytest.fixture()
def device_under_test(tango_context: DeviceTestContext) -> DeviceProxy:
    """
    Return a device proxy to the device under test.

    :param tango_context: a Tango test context with the specified device
        running
    :type tango_context: :py:class:`tango.DeviceTestContext`

    :return: a proxy to the device under test
    :rtype: :py:class:`tango.DeviceProxy`
    """
    # Give the PushChanges polled command time to run once.
    time.sleep(0.15)

    return tango_context.device


@pytest.fixture()
def callbacks() -> dict:
    """
    Return a dictionary of callbacks with asynchrony support.

    :return: a collections.defaultdict that returns callbacks by name.
    """
    return collections.defaultdict(MockCallable)


class ChangeEventDict:
    """Internal texting class that acts like a dictionary for creating mock callbacks."""

    def __init__(self: ChangeEventDict) -> None:
        """Initialise object."""
        self._dict: dict = {}

    def __getitem__(self: ChangeEventDict, key: Any) -> MockChangeEventCallback:
        """Get a mock change event callback to be used in testing."""
        if key not in self._dict:
            self._dict[key] = MockChangeEventCallback(key)
        return self._dict[key]


@pytest.fixture()
def change_event_callbacks() -> ChangeEventDict:
    """
    Return a dictionary of Tango device change event callbacks with asynchrony support.

    :return: a collections.defaultdict that returns change event
        callbacks by name.
    """
    return ChangeEventDict()


class TangoChangeEventHelper:
    """Internal testing class used for handling change events."""

    def __init__(
        self: TangoChangeEventHelper, device_under_test: DeviceProxy, change_event_callbacks: ChangeEventDict
    ) -> None:
        """Initialise change event helper."""
        self.device_under_test = device_under_test
        self.change_event_callbacks = change_event_callbacks

    def subscribe(self: TangoChangeEventHelper, attribute_name: str) -> MockChangeEventCallback:
        """Subscribe to change events of an attribute.

        This returns a :py:class:`MockChangeEventCallback` that can
        then be used to verify changes.
        """
        self.device_under_test.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            self.change_event_callbacks[attribute_name],
        )
        return self.change_event_callbacks[attribute_name]


@pytest.fixture()
def tango_change_event_helper(
    device_under_test: DeviceProxy, change_event_callbacks: ChangeEventDict
) -> TangoChangeEventHelper:
    """
    Return a helper to simplify subscription to the device under test with a callback.

    :param device_under_test: a proxy to the device under test
    :param change_event_callbacks: dictionary of callbacks with
        asynchrony support, specifically for receiving Tango device
        change events.
    """
    return TangoChangeEventHelper(
        device_under_test=device_under_test,
        change_event_callbacks=change_event_callbacks,
    )


@pytest.fixture()
def logger() -> logging.Logger:
    """Fixture that returns a default logger for tests."""
    return logging.Logger("Test logger")
