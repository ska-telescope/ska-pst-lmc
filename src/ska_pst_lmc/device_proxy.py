# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides a factory for :py:class:`tango.DeviceProxy` instances.

This code is based off the SKA TANGO Examples class.
"""

from __future__ import annotations

import functools
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Type

import backoff
import tango
from readerwriterlock import rwlock
from tango import DeviceProxy, GreenMode
from typing_extensions import TypedDict

BackoffDetailsType = TypedDict("BackoffDetailsType", {"args": list, "elapsed": float})


class ChangeEventSubscription:
    """Class to act as a handle for a change event subscription.

    Instances of this class can be used to programmatically unsubscribe from a change
    event, without having to have access to the device or the subscription id.
    """

    def __init__(
        self: ChangeEventSubscription,
        subscription_id: int,
        device: PstDeviceProxy,
        callbacks: List[Callable],
    ) -> None:
        """Initialise object.

        :param subscription_id: the id of the subscription.
        :param device: the `PstDeviceProxy` for which the subscription belongs to.
        """
        self._subscription_id = subscription_id
        self._device = device
        self._subscribed = True
        self._callbacks = callbacks

    @property
    def callbacks(self: ChangeEventSubscription) -> List[Callable]:
        """Get callbacks for current subscription."""
        return self._callbacks

    def __del__(self: ChangeEventSubscription) -> None:
        """Cleanup the subscription when object is getting deleted."""
        self.unsubscribe()

    def unsubscribe(self: ChangeEventSubscription) -> None:
        """Unsubscribe to the change event.

        Use this to method to unsubscribe to listening to a change event of
        as device. As this is potentially called from a Python thread this will
        try to run this within a Tango OmniThread using a background thread.
        """

        def _task() -> None:
            self._subscribed = False
            with tango.EnsureOmniThread():
                self._device.unsubscribe_event(self._subscription_id)

            self._callbacks.clear()

        if self._subscribed:
            thread = threading.Thread(target=_task)
            thread.start()
            thread.join()

    @property
    def subscribed(self: ChangeEventSubscription) -> bool:
        """Check if subscription is still subscribed."""
        return self._subscribed


class PstDeviceProxy:
    """A :py:class:`DeviceProxy` wrapper class.

    This class is used to wrap device proxies and abstract away from the TANGO
    API. This class is designed to provide passthrough methods/attributes that
    would already be available.

    At the moment this is a very simple API wrapper but could be built up, like
    what is done in MCCS that allows the device's to try to connect and wait for
    being initialised.
    """

    _device: DeviceProxy
    _fqdn: str
    _logger: logging.Logger

    def __init__(
        self: PstDeviceProxy,
        fqdn: str,
        logger: logging.Logger,
        device: DeviceProxy,
    ) -> None:
        """Initialise device proxy.

        :param fqdn: the fully qualified device-name of the TANGO device that the proxy is for.
        :param logger: the logger to use for logging within this proxy.
        :param device: the TANGO device proxy instance.
        """
        assert DeviceProxyFactory._raw_proxies.get(fqdn, None) == device, "Use DeviceProxyFactory.get_device"

        self.__dict__["_fqdn"] = fqdn
        self.__dict__["_logger"] = logger
        self.__dict__["_device"] = device
        self.__dict__["_subscriptions"] = {}
        self.__dict__["_lock"] = rwlock.RWLockWrite()

    def _event_callback(self: PstDeviceProxy, attribute_name: str, event: tango.EventData) -> None:
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
            value = self._read(attribute_name)
        else:
            value = event.attr_value

        if isinstance(value, tango.DeviceAttribute):
            value = value.value

        self._logger.info(f"Received event callback for {self.fqdn}.{attribute_name} with value: {value}")

        # read lock
        # with self._lock.gen_rlock():
        if attribute_name in self._subscriptions:
            [c(value) for c in self._subscriptions[attribute_name].callbacks]

    def _read(self: PstDeviceProxy, attribute_name: str) -> Any:
        """
        Read an attribute manually.

        Used when we receive an event with empty attribute data.

        :param attribute_name: the name of the attribute to be read

        :return: the attribute value
        """
        return self._device.read_attribute(attribute_name)

    def subscribe_change_event(
        self: PstDeviceProxy, attribute_name: str, callback: Callable, stateless: bool = False
    ) -> ChangeEventSubscription:
        """Subscribe to change events.

        This method is used to subscribe to an attribute changed event on the given proxy
            object. This is similar to:

        .. code-block:: python

            device.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                callback,
                stateless=stateless,
            )

        This method also returns a `ChangeEventSubscription` which can be used to
            later unsubscribe from change events on the device proxy.

        :param attribute_name: the name of the attribute on the device proxy to subscribe to.
        :param callback: the callback for TANGO to call when an event has happened.
        :param stateless: whether to use the TANGO stateless event model or not, default is True.
        :returns: a ChangeEventSubscription that can be used to later to unsubscribe from.
        """
        self._logger.info(f"Subscribing to events on {self.fqdn}.{attribute_name}")

        if attribute_name in self._subscriptions:
            self._subscriptions[attribute_name].callbacks.append(callback)
            value = self._read(attribute_name)
            callback(value.value)
        else:
            # write lock
            # with self._lock.gen_wlock():
            subscription_id = self._device.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                functools.partial(self._event_callback, attribute_name),
                stateless=stateless,
            )
            subscription = ChangeEventSubscription(
                subscription_id=subscription_id,
                device=self._device,
                callbacks=[callback],
            )
            self._subscriptions[attribute_name] = subscription

        return self._subscriptions[attribute_name]

    def __setattr__(self: PstDeviceProxy, name: str, value: Any) -> None:
        """Set attritube.

        :param name: name of attribute to set.
        :param value: the value of the attribute.
        """
        if name in ["fqdn", "logger"]:
            self.__dict__[f"_{name}"] = value
        else:
            setattr(self._device, name, value)

    def __getattr__(self: PstDeviceProxy, name: str) -> Any:
        """Get attribute value.

        :param name: the name of attribute to get.
        :returns: the value of the attribute.
        :raises: AttributeError if the attribute does not exist.
        """
        if name in ["fqdn", "logger"]:
            return self.__dict__[f"_{name}"]
        else:
            return getattr(self._device, name)

    @property
    def device(self: PstDeviceProxy) -> DeviceProxy:
        """Get Tango Device Proxy object."""
        return self._device


class DeviceProxyFactory:
    """
    Simple factory to create :py:class:`tango.DeviceProxy` instances.

    This class is an easy attempt to develop the concept developed by MCCS team
    in the following confluence page:
    https://confluence.skatelescope.org/display/SE/Running+BDD+tests+in+multiple+harnesses

    It is a factory class which provide the ability to create an object of
    type DeviceProxy. If a proxy had already been created it will reuse that
    instance.

    When testing the static variable _test_context is an instance of
    the TANGO class MultiDeviceTestContext.

    More information on tango testing can be found at the following link:
    https://pytango.readthedocs.io/en/stable/testing.html

    """

    _proxy_supplier: Callable[..., DeviceProxy] = tango.DeviceProxy
    _raw_proxies: Dict[str, DeviceProxy] = {}
    __proxies: Dict[str, PstDeviceProxy] = {}

    @classmethod
    def get_device(
        cls: Type[DeviceProxyFactory],
        fqdn: str,
        green_mode: GreenMode = GreenMode.Synchronous,
        logger: Optional[logging.Logger] = None,
    ) -> PstDeviceProxy:
        """Return a :py:class::`PstDeviceProxy`.

        This will return an existing proxy if already created, else it will
        create a `tango.DeviceProxy` and then wrap it as a :py:class::`PstDeviceProxy`.

        :param fqdn: the FQDN of the TANGO device that the proxy is for.
        :param green_mode: the TANGO green mode, the default is GreenMode.Synchronous.
        :param logger: the Python logger to use for the proxy.
        """
        if logger is None:
            logger = logging.getLogger(__name__)  # type: ignore

        def _on_giveup_connect(details: BackoffDetailsType) -> None:
            fqdn = details["args"][1]
            elapsed = details["elapsed"]
            logger.warning(  # type: ignore
                f"Gave up trying to connect to device {fqdn} after " f"{elapsed} seconds."
            )

        @backoff.on_exception(
            backoff.expo,
            tango.DevFailed,
            on_giveup=_on_giveup_connect,  # type: ignore
            factor=1,
            max_time=120.0,
        )
        def _get_proxy() -> tango.DeviceProxy:
            return cls._proxy_supplier(fqdn, green_mode=green_mode)

        if fqdn not in cls._raw_proxies:
            logger.debug(f"Creating new PstDeviceProxy for {fqdn}")
            try:
                cls._raw_proxies[fqdn] = _get_proxy()
            except Exception:
                cls._raw_proxies[fqdn] = cls._proxy_supplier(fqdn)

            cls.__proxies[fqdn] = PstDeviceProxy(fqdn=fqdn, logger=logger, device=cls._raw_proxies[fqdn])

        proxy = cls.__proxies[fqdn]
        return proxy
