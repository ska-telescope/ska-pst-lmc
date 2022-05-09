# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the RECV capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import List, Optional

import tango
from ska_tango_base.control_model import SimulationMode
from ska_tango_base.subarray import SKASubarray
from tango import DebugIt
from tango.server import attribute, command, run

import ska_pst_lmc.release as release
from ska_pst_lmc.smrb.smrb_component_manager import PstSmrbComponentManager

__all__ = ["PstSmrb", "main"]


class PstSmrb(SKASubarray):
    """A software TANGO device for managing the SMRB component of the PST.LMC subsystem.

    This TANGO device is used to manage the Shared Memory Ring Buffer (SMRB) for the
    PST.LMC subsystem.
    """

    # -----------------
    # Device Properties
    # -----------------

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstSmrb) -> None:
        """Initialise the attributes and properties of the PstReceive.

        This overrides the :py:class:`CspSubElementSubarray`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

    def create_component_manager(
        self: PstSmrb,
    ) -> PstSmrbComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstSmrbComponentManager(
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def always_executed_hook(self: PstSmrb) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstSmrb) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    # ------------------
    # Attributes
    # ------------------

    @attribute(
        dtype="DevFloat",
        label="Utilisation",
        unit="Percentage",
        display_unit="%",
        polling_period=5000,
        max_value=100,
        doc="Percentage of the ring buffer elements that are full of data",
    )
    def ring_buffer_utilisation(self: PstSmrb) -> float:
        """Get the percentage of the ring buffer elements that are full of data.

        :returns: the percentage of the ring buffer elements that are full of data.
        :rtype: float
        """
        return self.component_manager.ring_buffer_utilisation

    @attribute(
        dtype="DevULong64",
        label="Ring Buffer Size",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        polling_period=5000,
        doc="Capacity of ring buffer in bytes",
    )
    def ring_buffer_size(self: PstSmrb) -> int:
        """Get the capacity of the ring buffer, in bytes.

        :returns: the capacity of the ring buffer, in bytes.
        :rtype: int
        """
        return self.component_manager.ring_buffer_size

    @attribute(
        dtype="DevUShort",
        polling_period=5000,
        doc="Number of sub-bands",
    )
    def number_subbands(self: PstSmrb) -> int:
        """Get the number of sub-bands.

        :returns: the number of sub-bands.
        :rtype: int
        """
        return self.component_manager.number_subbands

    @attribute(
        dtype=("DevFloat",),
        max_dim_x=4,
        unit="Percent",
        standard_unit="Percent",
        display_unit="%",
        polling_period=5000,
        max_value=100,
        min_value=0,
        max_alarm=90,
        max_warning=80,
        doc="Percentage of full ring buffer elements for each sub-band",
    )
    def subband_ring_buffer_utilisations(self: PstSmrb) -> List[float]:
        """Get the percentage of full ring buffer elements for each sub-band.

        :returns: the percentage of full ring buffer elements for each sub-band.
        :rtype: List[float]
        """
        return self.component_manager.subband_ring_buffer_utilisations

    @attribute(
        dtype=("DevULong64",),
        max_dim_x=4,
        label="Sub-band ring buffer sizes",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        polling_period=5000,
        doc="Capacity of ring buffers, in bytes, for each sub-band",
    )
    def subband_ring_buffer_sizes(self: PstSmrb) -> List[int]:
        """Get the capacity of ring buffers for each sub-band.

        :returns: the capacity of ring buffers, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self.component_manager.subband_ring_buffer_sizes

    # --------
    # Commands
    # --------
    @command(
        dtype_out=("str",),
        doc_out="Version strings",
    )
    @DebugIt()
    def GetVersionInfo(self: PstSmrb) -> List[str]:
        """
        Return the version information of the device.

        :return: The result code and the command unique ID
        """
        return [f"{self.__class__.__name__}, {self.read_buildState()}"]


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
    return run((PstSmrb,), args=args, **kwargs)


if __name__ == "__main__":
    main()
