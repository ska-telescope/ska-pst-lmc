# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of SMRB."""

from ska_pst_lmc.smrb.smrb_util import calculate_smrb_subband_resources


def test_weights_for_demo() -> None:
    """Test calculation of weights."""
    request_params = {
        "num_frequency_channels": 11655,
        "num_of_polarizations": 2,
        "bits_per_sample": 16,
        "udp_nsamp": 4,
        "wt_nsamp": 4,
    }

    # want subband1
    actual = calculate_smrb_subband_resources(1, request_params=request_params)[1]

    expected = {
        "data_key": "0110",
        "weights_key": "0112",
        "hb_nbufs": 8,
        "hb_bufsz": 4096,
        "db_nbufs": 8,
        "db_bufsz": 33566400,
        "wb_nbufs": 8,
        "wb_bufsz": 4195800,
    }

    assert actual == expected
