# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the Beam capability for the Pulsar Timing Sub-element."""

from __future__ import annotations

from typing import List, Optional

import tango
from ska_tango_base.control_model import AdminMode, SimulationMode
from tango import DebugIt
from tango.server import command, device_property, run

import ska_pst_lmc.release as release
from ska_pst_lmc.beam.beam_component_manager import PstBeamComponentManager
from ska_pst_lmc.component.pst_device import PstBaseDevice

__all__ = ["PstBeam", "main"]


class PstBeam(PstBaseDevice):
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
        dtype=str,
    )

    RecvFQDN = device_property(
        dtype=str,
    )

    SmrbFQDN = device_property(
        dtype=str,
    )

    DspFQDN = device_property(
        dtype=str,
    )

    SendFQDN = device_property(
        dtype=str,
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstBeam) -> None:
        """Initialise the attributes and properties of the PstReceive.

        This overrides the :py:class:`SKABaseDevice`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

    def create_component_manager(
        self: PstBeam,
    ) -> PstBeamComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstBeamComponentManager(
            device_name=self.get_name(),
            smrb_fqdn=self.SmrbFQDN,
            recv_fqdn=self.RecvFQDN,
            dsp_fqdn=self.DspFQDN,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def always_executed_hook(self: PstBeam) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstBeam) -> None:
        """Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    # ----------
    # Attributes
    # ----------

    # --------
    # Commands
    # --------
    @command(
        dtype_out=("str",),
        doc_out="Version strings",
    )
    @DebugIt()
    def GetVersionInfo(self: PstBeam) -> List[str]:
        """
        Return the version information of the device.

        :return: The result code and the command unique ID
        """
        return [f"{self.__class__.__name__}, {self.read_buildState()}"]

    def _update_admin_mode(self: PstBeam, admin_mode: AdminMode) -> None:
        super()._update_admin_mode(admin_mode)
        if hasattr(self, "component_manager"):
            self.component_manager.update_admin_mode(admin_mode)


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
