# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing the SMRB capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

import dataclasses
from typing import Any, List, Optional

import tango
from ska_tango_base.control_model import SimulationMode
from tango import DebugIt
from tango.server import attribute, command, device_property, run

import ska_pst_lmc.release as release
from ska_pst_lmc.component import as_device_attribute_name
from ska_pst_lmc.component.pst_device import PstBaseProcessDevice
from ska_pst_lmc.smrb.smrb_component_manager import PstSmrbComponentManager
from ska_pst_lmc.smrb.smrb_model import SmrbMonitorData

__all__ = ["PstSmrb", "main"]


class PstSmrb(PstBaseProcessDevice[PstSmrbComponentManager, SmrbMonitorData]):
    """
    A software TANGO device for managing the SMRB component of the PST.LMC subsystem.

    This TANGO device is used to manage the Shared Memory Ring Buffer (SMRB) for the PST.LMC subsystem.
    """

    # -----------------
    # Device Properties
    # -----------------
    process_api_endpoint = device_property(dtype=str, doc="Endpoint for the SMRB.CORE service.")

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstSmrb) -> None:
        """
        Initialise the attributes and properties of the PstSmrb.

        This overrides the :py:class:`CspSubElementSubarray`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for f in dataclasses.fields(SmrbMonitorData):
            self.set_change_event(as_device_attribute_name(f.name), True, False)
            self.set_archive_event(as_device_attribute_name(f.name), True, False)

    def create_component_manager(
        self: PstSmrb,
    ) -> PstSmrbComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstSmrbComponentManager(
            device_interface=self,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
        )

    def always_executed_hook(self: PstSmrb) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstSmrb) -> None:
        """
        Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the init_device method to be
        released.  This method is called by the device destructor and by the device Init command.
        """

    def handle_monitor_data_update(self: PstSmrb, monitor_data: SmrbMonitorData) -> None:
        """
        Handle monitoring data.

        :param monitor_data: the latest monitoring data that has been reported.
        :type monitor_data: SmrbMonitorData
        """
        for (key, value) in dataclasses.asdict(monitor_data).items():
            self.handle_attribute_value_update(key, value)

    # ------------------
    # Attributes
    # ------------------

    @attribute(
        dtype=float,
        label="Utilisation",
        unit="Percentage",
        display_unit="%",
        max_value=100,
        min_value=0,
        max_alarm=90,
        max_warning=80,
        doc="Percentage of the ring buffer elements that are full of data",
    )
    def ringBufferUtilisation(self: PstSmrb) -> float:
        """
        Get the percentage of the ring buffer elements that are full of data.

        :returns: the percentage of the ring buffer elements that are full of data.
        :rtype: float
        """
        return self.component_manager.ring_buffer_utilisation

    @attribute(
        dtype=int,
        label="Ring Buffer Size",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Capacity of ring buffer in bytes",
    )
    def ringBufferSize(self: PstSmrb) -> int:
        """
        Get the capacity of the ring buffer, in bytes.

        :returns: the capacity of the ring buffer, in bytes.
        :rtype: int
        """
        return self.component_manager.ring_buffer_size

    @attribute(
        dtype=int,
        label="Ring Buffer Read",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Amount of data read from the ring buffer",
    )
    def ringBufferRead(self: PstSmrb) -> int:
        """
        Get the amount of data read from the ring buffer, in bytes.

        :returns: the amount of data read from then ring buffer, in bytes.
        :rtype: int
        """
        return self.component_manager.ring_buffer_read

    @attribute(
        dtype=int,
        label="Ring Buffer Written",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Amount of data written to ring buffer",
    )
    def ringBufferWritten(self: PstSmrb) -> int:
        """
        Get the amount of data written to the ring buffer, in bytes.

        :returns: the amount of data written to the ring buffer, in bytes.
        :rtype: int
        """
        return self.component_manager.ring_buffer_written

    @attribute(
        dtype=int,
        doc="Number of sub-bands",
    )
    def numberSubbands(self: PstSmrb) -> int:
        """
        Get the number of sub-bands.

        :returns: the number of sub-bands.
        :rtype: int
        """
        return self.component_manager.number_subbands

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        unit="Percent",
        standard_unit="Percent",
        display_unit="%",
        max_value=100,
        min_value=0,
        max_alarm=90,
        max_warning=80,
        doc="Percentage of full ring buffer elements for each sub-band",
    )
    def subbandRingBufferUtilisations(self: PstSmrb) -> List[float]:
        """
        Get the percentage of full ring buffer elements for each sub-band.

        :returns: the percentage of full ring buffer elements for each sub-band.
        :rtype: List[float]
        """
        return self.component_manager.subband_ring_buffer_utilisations

    @attribute(
        dtype=(int,),
        max_dim_x=4,
        label="Sub-band ring buffer sizes",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Capacity of ring buffers, in bytes, for each sub-band",
    )
    def subbandRingBufferSizes(self: PstSmrb) -> List[int]:
        """
        Get the capacity of ring buffers for each sub-band.

        :returns: the capacity of ring buffers, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self.component_manager.subband_ring_buffer_sizes

    @attribute(
        dtype=(int,),
        max_dim_x=4,
        label="Sub-band ring buffer read",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Amount of data read, in bytes, for each sub-band",
    )
    def subbandRingBufferRead(self: PstSmrb) -> List[int]:
        """
        Get the amount of data read, in bytes, for each sub-band.

        :returns: the amount of data read, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self.component_manager.subband_ring_buffer_read

    @attribute(
        dtype=(int,),
        max_dim_x=4,
        label="Sub-band ring buffer written",
        unit="Bytes",
        standard_unit="Bytes",
        display_unit="B",
        doc="Amount of data written, in bytes, for each sub-band",
    )
    def subbandRingBufferWritten(self: PstSmrb) -> List[int]:
        """
        Get the amount of data written, in bytes, for each sub-band.

        :returns: the amount of data written, in bytes, for each sub-band.
        :rtype: List[int]
        """
        return self.component_manager.subband_ring_buffer_written

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
        return [f"{self.__class__.__name__}, {self._build_state}"]


# ----------
# Run server
# ----------


def main(args: Optional[list] = None, **kwargs: Any) -> int:
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
