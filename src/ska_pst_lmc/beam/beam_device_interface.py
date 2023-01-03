# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module provides an purely abstract view the BEAM.MGMT Device."""

from __future__ import annotations

from ska_pst_lmc.component import PstDeviceInterface


class PstBeamDeviceInterface(PstDeviceInterface):
    """A purely abstract class that that represents a BEAM.MGMT Device.

    This is implemented by `PstBeam` and used by the `PstBeamComponentManager`
    which needs a limited view of the Tango device but without having full
    access to it.
    """

    @property
    def smrb_fqdn(self: PstBeamDeviceInterface) -> str:
        """Get the fully qualified device name (FQDN) for the SMRB.MGMT device of this beam."""
        raise NotImplementedError("PstBeamDeviceInterface is abstract")

    @property
    def recv_fqdn(self: PstBeamDeviceInterface) -> str:
        """Get the fully qualified device name (FQDN) for the RECV.MGMT device of this beam."""
        raise NotImplementedError("PstBeamDeviceInterface is abstract")

    @property
    def dsp_fqdn(self: PstBeamDeviceInterface) -> str:
        """Get the fully qualified device name (FQDN) for the DSP.MGMT device of this beam."""
        raise NotImplementedError("PstBeamDeviceInterface is abstract")

    def handle_subdevice_fault(self: PstBeamDeviceInterface, device_fqdn: str, fault_msg: str) -> None:
        """Handle a fault raised from a subordinate device.

        :param device_fqdn: the fully-qualified domain name of the subordinate device.
        :type device_fqdn: str
        :param fault_msg: the fault message from the subordinate device.
        :type fault_msg: str
        """
        raise NotImplementedError("PstBeamDeviceInterface is abstract")
