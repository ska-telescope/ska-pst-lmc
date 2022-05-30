"""This module defines elements of the pytest test harness shared by all tests."""
from __future__ import annotations

import collections
import logging
import time
from typing import Any, Callable, Generator
from unittest.mock import MagicMock

import pytest
import tango
from ska_tango_base.control_model import SimulationMode
from ska_tango_base.testing.mock import MockCallable, MockChangeEventCallback
from tango import DeviceProxy
from tango.test_context import DeviceTestContext, MultiDeviceTestContext, get_host_ip

from ska_pst_lmc.device_proxy import DeviceProxyFactory
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


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
    DeviceProxyFactory._proxy_supplier = tango_context.get_device
    tango_context.start()
    yield tango_context
    tango_context.stop()


@pytest.fixture(scope="class")
def server_configuration() -> dict:
    """Get server configuration for multi device test."""
    return {}


@pytest.fixture()
def multidevice_test_context(server_configuration: dict) -> Generator[MultiDeviceTestContext, None, None]:
    """Get generator for MultiDeviceTestContext."""

    def _get_port() -> int:
        import socket
        from contextlib import closing

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    if "host" not in server_configuration:
        server_configuration["host"] = get_host_ip()
    if "port" not in server_configuration:
        server_configuration["port"] = _get_port()
    if "timeout" not in server_configuration:
        server_configuration["timeout"] = 10

    def device_proxy_supplier(fqdn: str, *args: Any, **kwargs: Any) -> tango.DeviceProxy:
        if not fqdn.startswith("tango://"):
            host = server_configuration["host"]
            port = server_configuration["port"]

            fqdn = f"tango://{host}:{port}/{fqdn}#dbase=no"

        return tango.DeviceProxy(fqdn)

    DeviceProxyFactory._proxy_supplier = device_proxy_supplier

    with MultiDeviceTestContext(**server_configuration) as context:
        time.sleep(0.15)
        yield context


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


@pytest.fixture
def background_task_processor(
    logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> BackgroundTaskProcessor:
    """Create mock for background task processing."""

    def _submit_task(
        action_fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> MagicMock:
        action_fn()
        return MagicMock()

    # need to stub the submit_task and replace
    processor = BackgroundTaskProcessor(default_logger=logger)
    monkeypatch.setattr(processor, "submit_task", _submit_task)
    return processor


@pytest.fixture
def communication_state_callback() -> Callable:
    """Create a communication state callback."""
    return MagicMock()


@pytest.fixture
def component_state_callback() -> Callable:
    """Create a component state callback."""
    return MagicMock()


@pytest.fixture
def simulation_mode(request: pytest.FixtureRequest) -> SimulationMode:
    """Set simulation mode for test."""
    try:
        return request.param.get("simulation_mode", SimulationMode.TRUE)  # type: ignore
    except Exception:
        return SimulationMode.TRUE
