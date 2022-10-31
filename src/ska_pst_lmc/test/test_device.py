# -*- coding: utf-8 -*-
#
# See LICENSE.txt for more info.

"""Example Test Client that listens to events on a RECV device."""

from __future__ import annotations

import logging
from typing import Any, Optional

import tango
from tango.server import Device, DeviceMeta, attribute, device_property, run

from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy

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

    NumEventsReceived = attribute(
        dtype="int",
    )

    RecvFQDN = device_property(
        dtype=str,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstTestClient) -> None:
        """Initialise device."""
        super().init_device()
        self.logger = logging.getLogger(__name__)
        self.dev: Optional[PstDeviceProxy] = None
        self.attr_EventReceived = False
        self._num_events_received = 0

    def always_executed_hook(self: PstTestClient) -> None:
        """Ensure device proxy is setup."""
        try:
            if self.dev is None:
                self.logger.info("Connect to RECV device")
                self.dev = DeviceProxyFactory.get_device(self.RecvFQDN)
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

    def read_NumEventsReceived(self: PstTestClient) -> int:
        """Return number of events recevied."""
        return self._num_events_received

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
            self._num_events_received += 1
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


def main(args: Optional[list] = None, **kwargs: Any) -> int:
    """Run device server for PstTestClient device."""
    return run((PstTestClient,), args=args, **kwargs)


if __name__ == "__main__":
    main()
