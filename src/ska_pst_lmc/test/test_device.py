# -*- coding: utf-8 -*-
#
# See LICENSE.txt for more info.

""" PstTestClient

PstTestClient Training Example
"""

import logging

import tango
from ska_tango_base import SKABaseDevice
from tango.server import DeviceMeta, attribute, run

from ska_pst_lmc.device_proxy_factory import DeviceProxyFactory

__all__ = ["PstTestClient", "main"]


class PstTestClient(SKABaseDevice):
    """
    PstTestClient Training Example
    """

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

    def init_device(self):
        super().init_device()
        self.logger = logging.getLogger(__name__)
        self._dev_factory = DeviceProxyFactory()
        self.dev = None
        self.attr_EventReceived = False

    def always_executed_hook(self):
        try:
            if self.dev is None:
                self.logger.info("Connect to motor device")
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

    def delete_device(self):
        pass

    # ------------------
    # Attributes methods
    # ------------------

    def read_EventReceived(self):
        try:
            return self.attr_EventReceived
        except Exception as ex:
            self.logger.info(
                "Unexpected error on (self.attr_EventReceived = False): %s",
                str(ex),
            )

    # --------
    # Commands
    # --------

    def HandleEvent(self, args):
        try:
            self.logger.info(
                "Event arrived on obsState value= %s",
                str(self.dev.obsState),
            )
            self.logger.info("args = %s", str(args))
            self.attr_EventReceived = True
        except Exception as ex:
            self.logger.info(
                "Unexpected error on (self.attr_EventReceived = False): %s",
                str(ex),
            )


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return run((PstTestClient,), args=args, **kwargs)


if __name__ == "__main__":
    main()
