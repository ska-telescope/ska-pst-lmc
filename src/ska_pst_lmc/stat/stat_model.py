# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing common model classes within the STAT.MGMT component."""

from __future__ import annotations

from dataclasses import dataclass

from ska_pst_lmc.component import SUBBAND_1, MonitorDataStore


@dataclass(kw_only=True)
class StatMonitorData:
    """
    A data class to transfer current STAT scalar data between the process and the component manager.

    :ivar real_pol_a_mean_freq_avg: the mean voltage data across all channels for polarisation A and the I
        component
    :vartype real_pol_a_mean_freq_avg: float
    :ivar real_pol_a_variance_freq_avg: the variance of voltage data across all channels for polarisation A
        and the I component
    :vartype real_pol_a_variance_freq_avg: float
    :ivar real_pol_a_num_clipped_samples: the number of clipped samples across all channels for polarisation
        A and the I component
    :vartype real_pol_a_num_clipped_samples: int
    :ivar imag_pol_a_mean_freq_avg: the mean voltage data across all channels for polarisation A and the Q
        component
    :vartype imag_pol_a_mean_freq_avg: float
    :ivar imag_pol_a_variance_freq_avg: the variance of voltage data across all channels for polarisation A
        and the Q component
    :vartype imag_pol_a_variance_freq_avg: float
    :ivar imag_pol_a_num_clipped_samples: the number of clipped samples across all channels for polarisation
        A and the Q component
    :vartype imag_pol_a_num_clipped_samples: int
    :ivar real_pol_a_mean_freq_avg_rfi_excised: the mean voltage data across channels not flagged for RFI for
        polarisation A and the I component
    :vartype real_pol_a_mean_freq_avg_rfi_excised: float
    :ivar real_pol_a_variance_freq_avg_rfi_excised: the variance of voltage data across channels not flagged
        for RFI for polarisation A and the I component
    :vartype real_pol_a_variance_freq_avg_rfi_excised: float
    :ivar real_pol_a_num_clipped_samples_rfi_excised: the number of clipped samples across channels without
        RFI for polarisation A and the I component
    :vartype real_pol_a_num_clipped_samples_rfi_excised: int
    :ivar imag_pol_a_mean_freq_avg_rfi_excised: the mean voltage data across channels not flagged for RFI for
        polarisation A and the Q component
    :vartype imag_pol_a_mean_freq_avg_rfi_excised: float
    :ivar imag_pol_a_variance_freq_avg_rfi_excised: the variance of voltage data across channels not flagged
        for RFI for polarisation A and the Q component
    :vartype imag_pol_a_variance_freq_avg_rfi_excised: float
    :ivar imag_pol_a_num_clipped_samples_rfi_excised: the number of clipped samples across channels without
        RFI for polarisation A and the Q component
    :vartype imag_pol_a_num_clipped_samples_rfi_excised: int
    :ivar real_pol_b_mean_freq_avg: the mean voltage data across all channels for polarisation B and the I
        component
    :vartype real_pol_b_mean_freq_avg: float
    :ivar real_pol_b_variance_freq_avg: the variance of voltage data across all channels for polarisation B
        and the I component
    :vartype real_pol_b_variance_freq_avg: float
    :ivar real_pol_b_num_clipped_samples: the number of clipped samples across all channels for polarisation
        B and the I component
    :vartype real_pol_b_num_clipped_samples: int
    :ivar imag_pol_b_mean_freq_avg: the mean voltage data across all channels for polarisation B and the Q
        component
    :vartype imag_pol_b_mean_freq_avg: float
    :ivar imag_pol_b_variance_freq_avg: the variance of voltage data across all channels for polarisation B
        and the Q component
    :vartype imag_pol_b_variance_freq_avg: float
    :ivar imag_pol_b_num_clipped_samples: the number of clipped samples across all channels for polarisation
        B and the Q component
    :vartype imag_pol_b_num_clipped_samples: int
    :ivar real_pol_b_mean_freq_avg_rfi_excised: the mean voltage data across channels not flagged for RFI for
        polarisation B and the I component
    :vartype real_pol_b_mean_freq_avg_rfi_excised: float
    :ivar real_pol_b_variance_freq_avg_rfi_excised: the variance of voltage data across channels not flagged
        for RFI for polarisation B and the I component
    :vartype real_pol_b_variance_freq_avg_rfi_excised: float
    :ivar real_pol_b_num_clipped_samples_rfi_excised: the number of clipped samples across channels without
        RFI for polarisation B and the I component
    :vartype real_pol_b_num_clipped_samples_rfi_excised: int
    :ivar imag_pol_b_mean_freq_avg_rfi_excised: the mean voltage data across channels not flagged for RFI for
        polarisation B and the Q component
    :vartype imag_pol_b_mean_freq_avg_rfi_excised: float
    :ivar imag_pol_b_variance_freq_avg_rfi_excised: the variance of voltage data across channels not flagged
        for RFI for polarisation B and the Q component
    :vartype imag_pol_b_variance_freq_avg_rfi_excised: float
    :ivar imag_pol_b_num_clipped_samples_rfi_excised: the number of clipped samples across channels without
        RFI for polarisation B and the Q component
    :vartype imag_pol_b_num_clipped_samples_rfi_excised: int
    """

    # Pol A + I
    real_pol_a_mean_freq_avg: float = 0.0
    real_pol_a_variance_freq_avg: float = 0.0
    real_pol_a_num_clipped_samples: int = 0

    # Pol A + Q
    imag_pol_a_mean_freq_avg: float = 0.0
    imag_pol_a_variance_freq_avg: float = 0.0
    imag_pol_a_num_clipped_samples: int = 0

    # Pol A + I (RFI excised)
    real_pol_a_mean_freq_avg_rfi_excised: float = 0.0
    real_pol_a_variance_freq_avg_rfi_excised: float = 0.0
    real_pol_a_num_clipped_samples_rfi_excised: int = 0

    # Pol A + Q (RFI excised)
    imag_pol_a_mean_freq_avg_rfi_excised: float = 0.0
    imag_pol_a_variance_freq_avg_rfi_excised: float = 0.0
    imag_pol_a_num_clipped_samples_rfi_excised: int = 0

    # Pol B + I
    real_pol_b_mean_freq_avg: float = 0.0
    real_pol_b_variance_freq_avg: float = 0.0
    real_pol_b_num_clipped_samples: int = 0

    # Pol B + Q
    imag_pol_b_mean_freq_avg: float = 0.0
    imag_pol_b_variance_freq_avg: float = 0.0
    imag_pol_b_num_clipped_samples: int = 0

    # Pol B + I (RFI excised)
    real_pol_b_mean_freq_avg_rfi_excised: float = 0.0
    real_pol_b_variance_freq_avg_rfi_excised: float = 0.0
    real_pol_b_num_clipped_samples_rfi_excised: int = 0

    # Pol B + Q (RFI excised)
    imag_pol_b_mean_freq_avg_rfi_excised: float = 0.0
    imag_pol_b_variance_freq_avg_rfi_excised: float = 0.0
    imag_pol_b_num_clipped_samples_rfi_excised: int = 0


class StatMonitorDataStore(MonitorDataStore[StatMonitorData, StatMonitorData]):
    """
    A data store for STAT scalar subband monitoring data.

    This data store will aggregate the separate data. For now this only handles 1 subband as needed for AA0.5
    but for later array assembly releases this needs to aggregate the the separate subband data.
    """

    @property
    def monitor_data(self: StatMonitorDataStore) -> StatMonitorData:
        """
        Return the current calculated monitoring data.

        This aggregates all the individual subband data values into one
        :py:class:`StatMonitorData` instance.

        Currently this only supports 1 subband but in the future this will
        should support multiple subbands. This can be done by knowing the
        number of samples per statistic from each subband, including the
        total number and the number that has not been flagged as RFI.
        For more information about how this can be achieved refer to
        `Wikipedia - Algorithms for calculating variance - Parallel algorithm
        <https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Parallel_algorithm>`_

        :returns: current monitoring data.
        """
        number_subbands: int = len(self._subband_data)
        if number_subbands == 0:
            return StatMonitorData()

        # for now we only have 1 subband
        return self._subband_data[SUBBAND_1]
