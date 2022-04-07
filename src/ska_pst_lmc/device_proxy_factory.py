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
from typing import Dict, Optional

from tango import DeviceProxy, GreenMode


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

    _test_context = None

    def __init__(self: DeviceProxyFactory, green_mode: GreenMode = GreenMode.Synchronous) -> None:
        """Initialise the factory.

        :param green_mode: the type of green threading to use for the :py:class:`tango.DeviceProxy` instances.
        """
        self.dev_proxys: Dict[str, DeviceProxy] = {}
        self.logger = logging.getLogger(__name__)
        self.default_green_mode = green_mode

    def get_device(
        self: DeviceProxyFactory, dev_name: str, green_mode: Optional[GreenMode] = None
    ) -> DeviceProxy:
        """
        Get a `DeviceProxy` instance for a given the device's fully qualified name (FQNM).

        This method will return the same instance of a `DeviceProxy` if it has alreadyt
        been created.

        :param dev_name: the device name.
        :type dev_name: str
        :param green_mode: the type of green thread mode, default is synchronous.
        :type green_mode: :py:class:`tango.GreenMode`

        :returns: a device proxy.
        :rtype: :py:class:`tango.DeviceProxy`
        """
        if green_mode is None:
            green_mode = self.default_green_mode

        if DeviceProxyFactory._test_context is None:
            if dev_name not in self.dev_proxys:
                self.logger.info("Creating Proxy for %s", dev_name)
                self.dev_proxys[dev_name] = DeviceProxy(dev_name, green_mode=green_mode)
            return self.dev_proxys[dev_name]
        else:
            return DeviceProxyFactory._test_context.get_device(dev_name)
