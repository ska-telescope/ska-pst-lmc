# -*- coding: utf-8 -*-
#
# This file is part of the PstReceive project
#
#
#
# Distributed under the terms of the BSD3 license.
# See LICENSE.txt for more info.

"""Module for providing the RECV capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import List, Optional

from ska_tango_base.csp.subarray import CspSubElementSubarray
from tango.server import attribute, run

__all__ = ["PstReceive", "main"]


class PstReceive(CspSubElementSubarray):
    """A software TANGO device for managing the RECV component of the PST.LMC subsystem."""

    # -----------------
    # Device Properties
    # -----------------

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstReceive) -> None:
        """Initialise the attributes and properties of the PstReceive.

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

    def always_executed_hook(self: PstReceive) -> None:
        """Execute call before any TANGO command is executed."""
        pass

    def delete_device(self: PstReceive) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        pass

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="DevFloat",
        unit="Gigabits per second",
        standard_unit="Gigabits per second",
        display_unit="Gb/s",
        polling_period=5000,
        max_value=200,
        min_value=0,
        doc="Current data receive rate from the CBF interface",
    )
    def received_rate(self: PstReceive) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return 0.0

    @attribute(
        dtype="DevULong64",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        polling_period=5000,
        doc="Total number of bytes received from the CBF in the current scan",
    )
    def received_data(self: PstReceive) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return 0

    @attribute(
        dtype="DevFloat",
        label="Drop Rate",
        unit="Megabits per second",
        standard_unit="Megabits per second",
        display_unit="MB/s",
        polling_period=5000,
        max_value=200,
        min_value=-1,
        max_alarm=10,
        min_alarm=-1,
        max_warning=1,
        min_warning=-1,
        doc="Current rate of CBF ingest data being dropped or lost by the receiving process",
    )
    def dropped_rate(self: PstReceive) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return 0.0

    @attribute(
        dtype="DevULong64",
        label="Dropped",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        polling_period=5000,
        doc="Total number of bytes dropped in the current scan",
    )
    def dropped(self: PstReceive) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return 0

    @attribute(
        dtype="DevULong64",
        label="Out of order packets",
        polling_period=5000,
        doc="The total number of packets received out of order in the current scan",
    )
    def misordered_packets(self: PstReceive) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return 0

    @attribute(
        dtype="DevULong64",
        polling_period=5000,
        doc="Total number of malformed packets received during the current scan",
    )
    def malformed_packets(self: PstReceive) -> int:
        """Get the total number of malformed packets received during the current scan.

        :returns: total number of malformed packets received during the current scan.
        :rtype: int
        """
        return 0

    @attribute(
        dtype="DevFloat",
        polling_period=5000,
        doc="Time average of all relative weights for the current scan",
    )
    def relative_weight(self: PstReceive) -> float:
        """Get the time averages of all relative weights for the current scan.

        :returns: time average of all relative weights for the current scan.
        :rtype: float
        """
        return 0.0

    @attribute(
        dtype=("DevFloat",),
        max_dim_x=1024,
        polling_period=5000,
        min_value=0,
        doc="Time average of relative weights for each channel in the current scan",
    )
    def relative_weights(self: PstReceive) -> List[float]:
        """Get the time average of relative weights for each channel in the current scan.

        :returns: time average of relative weights for each channel in the current scan.
        :rtype: list(float)
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
    return run((PstReceive,), args=args, **kwargs)


if __name__ == "__main__":
    main()
