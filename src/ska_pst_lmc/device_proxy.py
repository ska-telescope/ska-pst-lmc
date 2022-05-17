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

import logging
import threading
from typing import Any, Callable, Dict, Optional, Type

import tango
from tango import DeviceProxy, GreenMode


class ChangeEventSubscription:
    """Class to act as a handle for a change event subscription.

    Instances of this class can be used to programmatically unsubscribe from a change
    event, without having to have access to the device or the subscription id.
    """

    def __init__(self: ChangeEventSubscription, subscription_id: int, device: PstDeviceProxy) -> None:
        """Initialise object.

        :param subscription_id: the id of the subscription.
        :param device: the `PstDeviceProxy` for which the subscription belongs to.
        """
        self._subscription_id = subscription_id
        self._device = device
        self._subscribed = True

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

    def subscribe_change_event(
        self: PstDeviceProxy, attribute_name: str, callback: Callable, stateless: bool = True
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
        subscription_id = self._device.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            callback,
            stateless=stateless,
        )

        return ChangeEventSubscription(
            subscription_id=subscription_id,
            device=self._device,
        )

    def __setattr__(self: PstDeviceProxy, name: str, value: Any) -> None:
        """Set attritube.

        :param name: name of attribute to set.
        :param value: the value of the attribute.
        """
        if name in ["fqdn", "logger"]:
            self.__dict__[f"_{name}"] = value
        else:
            setattr(self._device, name, value)

    def __getattr__(self, name: str) -> Any:
        """Get attribute value.

        :param name: the name of attribute to get.
        :returns: the value of the attribute.
        :raises: AttributeError if the attribute does not exist.
        """
        if name in ["fqdn", "logger"]:
            return self.__dict__[f"_{name}"]
        else:
            return getattr(self._device, name)


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
        logger = logger or logging.getLogger(__name__)

        if fqdn not in cls._raw_proxies:
            cls._raw_proxies[fqdn] = cls._proxy_supplier(fqdn, green_mode=green_mode)
            cls.__proxies[fqdn] = PstDeviceProxy(fqdn=fqdn, logger=logger, device=cls._raw_proxies[fqdn])

        return cls.__proxies[fqdn]
