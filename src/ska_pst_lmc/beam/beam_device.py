# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Beam capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import Optional

from ska_tango_base.csp.subarray import CspSubElementSubarray
from tango.server import device_property, run

# PyTango imports
# from tango import AttrQuality, AttrWriteType, DebugIt, DevState, DispLevel, PipeWriteType
# from tango.server import Device, attribute, command, device_property, run

__all__ = ["PstBeam", "main"]


class PstBeam(CspSubElementSubarray):
    """A logical TANGO device representing a Beam Capability for PST.LMC.

    **Properties:**

    - Device Property
        beam_id
            - Type:'DevString'
        RecvFQDN
            - Type:'DevString'
        SmrbFQDN
            - Type:'DevString'
        DspFQDN
            - Type:'DevString'
        SendFQDN
            - Type:'DevString'
    """

    # -----------------
    # Device Properties
    # -----------------

    beam_id = device_property(
        dtype="DevString",
    )

    RecvFQDN = device_property(
        dtype="DevString",
    )

    SmrbFQDN = device_property(
        dtype="DevString",
    )

    DspFQDN = device_property(
        dtype="DevString",
    )

    SendFQDN = device_property(
        dtype="DevString",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstBeam) -> None:
        """Intialise the attributes and properties of the PstBeam device.

        This overrides the :py:class::`CspSubElementSubarray`.
        """
        CspSubElementSubarray.init_device(self)
        self.set_change_event("adminMode", True, True)
        self.set_archive_event("adminMode", True, True)
        self.set_change_event("obsState", True, True)
        self.set_archive_event("obsState", True, True)
        self.set_change_event("longRunningCommandsInQueue", True, True)
        self.set_change_event("longRunningCommandStatus", True, True)
        self.set_change_event("longRunningCommandProgress", True, True)
        self.set_change_event("longRunningCommandResult", True, True)

    def always_executed_hook(self: PstBeam) -> None:
        """Execute call before any TANGO command is executed."""
        pass

    def delete_device(self: PstBeam) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        pass

    # ----------
    # Attributes
    # ----------

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
    return run((PstBeam,), args=args, **kwargs)


if __name__ == "__main__":
    main()
