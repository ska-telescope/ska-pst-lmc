# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing the STAT capability for the Pulsar Timing Sub-element."""

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
from ska_pst_lmc.stat.stat_component_manager import PstStatComponentManager
from ska_pst_lmc.stat.stat_model import StatMonitorData

__all__ = ["PstStat", "main"]


class PstStat(PstBaseProcessDevice[PstStatComponentManager, StatMonitorData]):
    """
    A software TANGO device for managing the STAT component of the PST.LMC subsystem.

    This TANGO device is used to manage the statistics computation (STAT) for the PST.LMC subsystem.
    """

    # -----------------
    # Device Properties
    # -----------------
    process_api_endpoint = device_property(dtype=str, doc="Endpoint for the STAT.CORE service.")

    # ---------------
    # General methods
    # ---------------

    def init_device(self: PstStat) -> None:
        """
        Initialise the attributes and properties of the PstStat.

        This overrides the :py:class:`CspSubElementSubarray`.
        """
        util = tango.Util.instance()
        util.set_serial_model(tango.SerialModel.NO_SYNC)
        super().init_device()
        self._build_state = "{}, {}, {}".format(release.NAME, release.VERSION, release.DESCRIPTION)
        self._version_id = release.VERSION

        for f in dataclasses.fields(StatMonitorData):
            self.set_change_event(as_device_attribute_name(f.name), True, False)
            self.set_archive_event(as_device_attribute_name(f.name), True, False)

    def create_component_manager(
        self: PstStat,
    ) -> PstStatComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """
        return PstStatComponentManager(
            device_interface=self,
            simulation_mode=SimulationMode.TRUE,
            logger=self.logger,
        )

    def always_executed_hook(self: PstStat) -> None:
        """Execute call before any TANGO command is executed."""

    def delete_device(self: PstStat) -> None:
        """
        Delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the init_device method to be
        released.  This method is called by the device destructor and by the device Init command.
        """

    def handle_monitor_data_update(self: PstStat, monitor_data: StatMonitorData) -> None:
        """
        Handle monitoring data.

        :param monitor_data: the latest monitoring data that has been reported.
        :type monitor_data: StatMonitorData
        """
        for (key, value) in dataclasses.asdict(monitor_data).items():
            self.handle_attribute_value_update(key, value)

    # ------------------
    # Attributes
    # ------------------

    @attribute(
        dtype=float,
        label="Real Pol. A Mean",
    )
    def realPolAMeanFreqAvg(self: PstStat) -> float:
        """Get the mean of the real data for pol A, averaged over all channels."""
        return self.component_manager.real_pol_a_mean_freq_avg

    @attribute(
        dtype=float,
        label="Real Pol. A Variance",
    )
    def realPolAVarianceFreqAvg(self: PstStat) -> float:
        """Get the variance of the real data for pol A, averaged over all channels."""
        return self.component_manager.real_pol_a_variance_freq_avg

    @attribute(
        dtype=int,
        label="Real Pol. A Num. Clipped",
    )
    def realPolANumClippedSamples(self: PstStat) -> int:
        """Get the num of clipped samples of the real data for pol A."""
        return self.component_manager.real_pol_a_num_clipped_samples

    @attribute(
        dtype=float,
        label="Imaginary Pol. A Mean",
    )
    def imagPolAMeanFreqAvg(self: PstStat) -> float:
        """Get the mean of the imaginary data for pol A, averaged over all channels."""
        return self.component_manager.imag_pol_a_mean_freq_avg

    @attribute(
        dtype=float,
        label="Imaginary Pol. A Variance",
    )
    def imagPolAVarianceFreqAvg(self: PstStat) -> float:
        """Get the variance of the imaginary data for pol A, averaged over all channels."""
        return self.component_manager.imag_pol_a_variance_freq_avg

    @attribute(
        dtype=int,
        label="Imaginary Pol. A Num. Clipped",
    )
    def imagPolANumClippedSamples(self: PstStat) -> int:
        """Get the num of clipped samples of the imaginary data for pol A."""
        return self.component_manager.imag_pol_a_num_clipped_samples

    @attribute(
        dtype=float,
        label="Real Pol. A Mean (RFI excised)",
    )
    def realPolAMeanFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the mean of the real data for pol A, averaged over channels without RFI."""
        return self.component_manager.real_pol_a_mean_freq_avg_rfi_excised

    @attribute(
        dtype=float,
        label="Real Pol. A Variance (RFI excised)",
    )
    def realPolAVarianceFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the variance of the real data for pol A, averaged over channels without RFI."""
        return self.component_manager.real_pol_a_variance_freq_avg_rfi_excised

    @attribute(
        dtype=int,
        label="Real Pol. A Num. Clipped (RFI excised)",
    )
    def realPolANumClippedSamplesRfiExcised(self: PstStat) -> int:
        """Get the num of clipped samples of the real data for pol A in channels without RFI."""
        return self.component_manager.real_pol_a_num_clipped_samples_rfi_excised

    @attribute(
        dtype=float,
        label="Imaginary Pol. A Mean (RFI excised)",
    )
    def imagPolAMeanFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the mean of the imaginary data for pol A, averaged over channels without RFI."""
        return self.component_manager.imag_pol_a_mean_freq_avg_rfi_excised

    @attribute(
        dtype=float,
        label="Imaginary Pol. A Variance (RFI excised)",
    )
    def imagPolAVarianceFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the variance of the imaginary data for pol A, averaged over channels without RFI."""
        return self.component_manager.imag_pol_a_variance_freq_avg_rfi_excised

    @attribute(
        dtype=int,
        label="Imaginary Pol. A Num. Clipped (RFI excised)",
    )
    def imagPolANumClippedSamplesRfiExcised(self: PstStat) -> int:
        """Get the num of clipped samples of the imaginary data for pol A in channels without RFI."""
        return self.component_manager.imag_pol_a_num_clipped_samples_rfi_excised

    @attribute(
        dtype=float,
        label="Real Pol. B Mean",
    )
    def realPolBMeanFreqAvg(self: PstStat) -> float:
        """Get the mean of the real data for pol B, averaged over all channels."""
        return self.component_manager.real_pol_b_mean_freq_avg

    @attribute(
        dtype=float,
        label="Real Pol. B Variance",
    )
    def realPolBVarianceFreqAvg(self: PstStat) -> float:
        """Get the variance of the real data for pol B, averaged over all channels."""
        return self.component_manager.real_pol_b_variance_freq_avg

    @attribute(
        dtype=int,
        label="Real Pol. B Num. Clipped",
    )
    def realPolBNumClippedSamples(self: PstStat) -> int:
        """Get the num of clipped samples of the real data for pol B."""
        return self.component_manager.real_pol_b_num_clipped_samples

    @attribute(
        dtype=float,
        label="Imaginary Pol. B Mean",
    )
    def imagPolBMeanFreqAvg(self: PstStat) -> float:
        """Get the mean of the imaginary data for pol B, averaged over all channels."""
        return self.component_manager.imag_pol_b_mean_freq_avg

    @attribute(
        dtype=float,
        label="Imaginary Pol. B Variance",
    )
    def imagPolBVarianceFreqAvg(self: PstStat) -> float:
        """Get the variance of the imaginary data for pol B, averaged over all channels."""
        return self.component_manager.imag_pol_b_variance_freq_avg

    @attribute(
        dtype=int,
        label="Imaginary Pol. B Num. Clipped",
    )
    def imagPolBNumClippedSamples(self: PstStat) -> int:
        """Get the num of clipped samples of the imaginary data for pol B."""
        return self.component_manager.imag_pol_b_num_clipped_samples

    @attribute(
        dtype=float,
        label="Real Pol. B Mean (RFI excised)",
    )
    def realPolBMeanFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the mean of the real data for pol B, averaged over channels without RFI."""
        return self.component_manager.real_pol_b_mean_freq_avg_rfi_excised

    @attribute(
        dtype=float,
        label="Real Pol. B Variance (RFI excised)",
    )
    def realPolBVarianceFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the variance of the real data for pol B, averaged over channels without RFI."""
        return self.component_manager.real_pol_b_variance_freq_avg_rfi_excised

    @attribute(
        dtype=int,
        label="Real Pol. B Num. Clipped (RFI excised)",
    )
    def realPolBNumClippedSamplesRfiExcised(self: PstStat) -> int:
        """Get the num of clipped samples of the real data for pol B in channels without RFI."""
        return self.component_manager.real_pol_b_num_clipped_samples_rfi_excised

    @attribute(
        dtype=float,
        label="Imaginary Pol. B Mean (RFI excised)",
    )
    def imagPolBMeanFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the mean of the imaginary data for pol B, averaged over channels without RFI."""
        return self.component_manager.imag_pol_b_mean_freq_avg_rfi_excised

    @attribute(
        dtype=float,
        label="Imaginary Pol. B Variance (RFI excised)",
    )
    def imagPolBVarianceFreqAvgRfiExcised(self: PstStat) -> float:
        """Get the variance of the imaginary data for pol B, averaged over channels without RFI."""
        return self.component_manager.imag_pol_b_variance_freq_avg_rfi_excised

    @attribute(
        dtype=int,
        label="Imaginary Pol. B Num. Clipped (RFI excised)",
    )
    def imagPolBNumClippedSamplesRfiExcised(self: PstStat) -> int:
        """Get the num of clipped samples of the imaginary data for pol B in channels without RFI."""
        return self.component_manager.imag_pol_b_num_clipped_samples_rfi_excised

    # --------
    # Commands
    # --------
    @command(
        dtype_out=("str",),
        doc_out="Version strings",
    )
    @DebugIt()
    def GetVersionInfo(self: PstStat) -> List[str]:
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
    :return: exit code :rtype-> int:
    """
    return run((PstStat,), args=args, **kwargs)


if __name__ == "__main__":
    main()
