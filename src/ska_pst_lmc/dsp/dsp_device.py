# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Beam capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import List, Optional

from ska_tango_base.csp.subarray import CspSubElementSubarray
from tango.server import attribute, run

__all__ = ["PstDsp", "main"]


class PstDsp(CspSubElementSubarray):
    """A TANGO device for integrating with the the Digital Signal Processing sub-sub-element for PST.LMC.

    **Properties:**

    - Device Property
    """

    # -----------------
    # Device Properties
    # -----------------

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstDsp) -> None:
        """Initialise the attributes and properties of the PstDsp."""
        CspSubElementSubarray.init_device(self)
        self.set_change_event("adminMode", True, True)
        self.set_archive_event("adminMode", True, True)
        self.set_change_event("obsState", True, True)
        self.set_archive_event("obsState", True, True)
        self.set_change_event("longRunningCommandsInQueue", True, True)
        self.set_change_event("longRunningCommandStatus", True, True)
        self.set_change_event("longRunningCommandProgress", True, True)
        self.set_change_event("longRunningCommandResult", True, True)

    def always_executed_hook(self: PstDsp) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstDsp) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevFloat",
        polling_period=5000,
    )
    def utilisation(self: PstDsp) -> float:
        """Get the utilisation of DSP.

        :returns: the utilisation, as a percentage, of the DSP subsystem.
        :rtype: float
        """
        return 0.0

    @attribute(
        dtype="DevFloat",
        unit="percentage",
        display_unit="%",
        polling_period=5000,
        max_value=100,
        min_value=0,
        max_alarm=90,
        max_warning=50,
        doc="Percentage of output data flagged as RFI by DSP",
    )
    def output_rfi(self: PstDsp) -> float:
        """Get the percentage of output data flagged as RFI by DSP.

        :returns: percentage of output data flagged as RFI.
        :rtype: float
        """
        return 0.0

    @attribute(
        dtype=("DevFloat",),
        max_dim_x=4,
        polling_period=5000,
    )
    def subband_utilisation(self: PstDsp) -> List[float]:
        """Get the subband utilisation.

        :returns: the utilisation of each subband. Max of 4 elements in list.
        :rtype: list
        """
        return [0.0]

    @attribute(
        dtype=("DevDouble",),
        max_dim_x=4096,
        label="Output Channel RFI Percentage",
        unit="percentage",
        standard_unit="percentage",
        display_unit="%",
        polling_period=5000,
        doc="Percentage of data flagged as RFI for each output channel, averaged over each sub-integration",
    )
    def output_rfi_spectrum(self: PstDsp) -> List[float]:
        """Get the percentage of RFI for each channel.

        :returns: the percentage of RFI for each channel averaged over the sub-integration.
        :rtype: list
        """
        return [0.0]

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
    return run((PstDsp,), args=args, **kwargs)


if __name__ == "__main__":
    main()
