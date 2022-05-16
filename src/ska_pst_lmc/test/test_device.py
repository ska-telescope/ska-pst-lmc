# -*- coding: utf-8 -*-
#
# See LICENSE.txt for more info.

"""Example Test Client that listens to events on a RECV device."""

from __future__ import annotations

import logging
from typing import Any, Optional

import tango
from tango import DeviceProxy
from tango.server import Device, DeviceMeta, attribute, run

from ska_pst_lmc.device_proxy_factory import DeviceProxyFactory

__all__ = ["PstTestClient", "main"]


class PstTestClient(Device):
    """Example Test Client that listens to events on a RECV device."""

    __metaclass__ = DeviceMeta

    # ----------
    # Attributes
    # ----------

    EventReceived = attribute(
        dtype="bool",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstTestClient) -> None:
        """Initialise device."""
        super().init_device()
        self.logger = logging.getLogger(__name__)
        self._dev_factory = DeviceProxyFactory()
        self.dev: Optional[DeviceProxy] = None
        self.attr_EventReceived = False

    def always_executed_hook(self: PstTestClient) -> None:
        """Ensure device proxy is setup."""
        try:
            if self.dev is None:
                self.logger.info("Connect to RECV device")
                self.dev = self._dev_factory.get_device("test/receive/1")
                self.attr_EventReceived = False
                self.logger.info("subscribe_event on obsState")
                self.dev.subscribe_event(
                    "obsState",
                    tango.EventType.CHANGE_EVENT,
                    self.HandleEvent,
                    stateless=True,
                )
        except Exception as ex:
            self.logger.info("Unexpected error: %s", str(ex))

    def delete_device(self: PstTestClient) -> None:
        """Handle device being deleted."""

    # ------------------
    # Attributes methods
    # ------------------

    def read_EventReceived(self: PstTestClient) -> bool:
        """Return value of EventReceviced attribute."""
        try:
            return self.attr_EventReceived
        except Exception as ex:
            self.logger.info(
                "Unexpected error on (self.attr_EventReceived = False): %s",
                str(ex),
            )
            raise ex

    # --------
    # Commands
    # --------

    def HandleEvent(self: PstTestClient, args: Any) -> None:
        """Handle event raised."""
        try:
            self.logger.info(
                "Event arrived on obsState value= %s",
                str(self.dev.obsState),  # type: ignore
            )
            self.logger.info("args = %s", str(args))
            self.attr_EventReceived = True
        except Exception as ex:
            self.logger.info(
                "Unexpected error on (self.attr_EventReceived = False): %s",
                str(ex),
            )
            raise ex


# ----------
# Run server
# ----------


def main(args: Optional[list] = None, **kwargs: dict) -> int:
    """Run device server for PstTestClient device."""
    return run((PstTestClient,), args=args, **kwargs)


if __name__ == "__main__":
    main()
