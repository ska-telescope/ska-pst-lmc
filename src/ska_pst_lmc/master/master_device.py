# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module implements the PstMaster device."""

from __future__ import annotations

from typing import Optional

from ska_tango_base.csp.controller_device import CspSubElementController
from tango.server import device_property, run

# PyTango imports
# from tango import AttrQuality, AttrWriteType, DebugIt, DevState, DispLevel, PipeWriteType
# from tango.server import Device, attribute, command, device_property, run

__all__ = ["PstMaster", "main"]


class PstMaster(CspSubElementController):
    """An implementation of a Maser Tango device for PST.LMC.

    **Properties:**

    - Device Property
        BeamFQDN
            - Address of the Beam capability TANGO device
            - Type:'DevString'
        BeamServerFQDN
            - Address of the BeamServer TANGO device
            - Type:'DevString'
    """

    # -----------------
    # Device Properties
    # -----------------
    BeamFQDN = device_property(
        dtype="DevString",
    )
    BeamServerFQDN = device_property(
        dtype="DevString",
    )

    # ----------
    # Attributes
    # ----------

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstMaster) -> None:
        """Intialise the attributes and properties of the PstMaster device.

        This overrides the :py:class::`CspSubElementController`.
        """
        CspSubElementController.init_device(self)
        self.set_change_event("adminMode", True, True)
        self.set_archive_event("adminMode", True, True)
        self.set_change_event("longRunningCommandsInQueue", True, True)
        self.set_change_event("longRunningCommandStatus", True, True)
        self.set_change_event("longRunningCommandProgress", True, True)
        self.set_change_event("longRunningCommandResult", True, True)

    # ------------------
    # Attributes methods
    # ------------------

    # --------
    # Commands
    # --------


# ----------
# Run server
# ----------


def main(args: Optional[list] = None, **kwargs: dict) -> int:
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments

    :return: exit code
    :rtype: int
    """
    return run((PstMaster,), args=args, **kwargs)


if __name__ == "__main__":
    main()
