# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the SMRB utility methods."""


from typing import Any, Dict, Optional

import pytest

from ska_pst_lmc.smrb.smrb_util import (
    calculate_smrb_subband_resources,
    generate_data_key,
    generate_weights_key,
)


@pytest.mark.parametrize(
    "beam_id, subband_id, expected_key",
    [
        (1, 1, "0110"),
        (2, 1, "0210"),
        (3, 1, "0310"),
        (4, 1, "0410"),
        (5, 2, "0520"),
        (6, 2, "0620"),
        (7, 2, "0720"),
        (8, 2, "0820"),
        (9, 3, "0930"),
        (10, 3, "0a30"),
        (11, 3, "0b30"),
        (12, 3, "0c30"),
        (13, 4, "0d40"),
        (14, 4, "0e40"),
        (15, 4, "0f40"),
        (16, 4, "1040"),
    ],
)
def test_generate_data_key(beam_id: int, subband_id: int, expected_key: str) -> None:
    """Test generating SMRB data keys."""
    actual = generate_data_key(beam_id=beam_id, subband_id=subband_id)
    assert actual == expected_key


@pytest.mark.parametrize(
    "beam_id, subband_id, expected_key",
    [
        (1, 1, "0112"),
        (2, 1, "0212"),
        (3, 1, "0312"),
        (4, 1, "0412"),
        (5, 2, "0522"),
        (6, 2, "0622"),
        (7, 2, "0722"),
        (8, 2, "0822"),
        (9, 3, "0932"),
        (10, 3, "0a32"),
        (11, 3, "0b32"),
        (12, 3, "0c32"),
        (13, 4, "0d42"),
        (14, 4, "0e42"),
        (15, 4, "0f42"),
        (16, 4, "1042"),
    ],
)
def test_generate_weights_key(beam_id: int, subband_id: int, expected_key: str) -> None:
    """Test generating SMRB weights keys."""
    actual = generate_weights_key(beam_id=beam_id, subband_id=subband_id)
    assert actual == expected_key


@pytest.mark.parametrize(
    "frequency_band, nchan, nbits, udp_nsamp, wt_nsamp, db_bufsz, wb_bufsz, num_of_buffers",
    [
        (None, 82944, 32, 32, 32, 339738624, 2875392, 64),
        ("0", 82944, 32, 32, 32, 339738624, 2875392, 64),
        ("1", 13021, 32, 4, 4, 426672128, 28887040, 128),
        ("2", 15067, 32, 4, 4, 493715456, 33425408, 128),
        ("3", 26042, 24, 4, 4, 320004096, 28889088, 256),
        ("4", 44271, 16, 4, 4, 362668032, 49110016, 256),
        ("5a", 46503, 16, 4, 4, 380952576, 51586048, 256),
        ("5b", 46503, 16, 4, 4, 380952576, 51586048, 256),
    ],
)
def test_calculate_ringbuffer_sizes(
    frequency_band: Optional[str],
    nchan: int,
    nbits: int,
    udp_nsamp: int,
    wt_nsamp: int,
    db_bufsz: int,
    wb_bufsz: int,
    num_of_buffers: int,
    configure_scan_request: Dict[str, Any],
) -> None:
    """Test calculating of data and weight buffer sizes."""
    configure_scan_request["num_of_polarizations"]

    request_params = {
        **configure_scan_request,
        "num_frequency_channels": nchan,
        "frequency_band": frequency_band,
        "bits_per_sample": nbits,
        "udp_nsamp": udp_nsamp,
        "wt_nsamp": wt_nsamp,
    }

    output = calculate_smrb_subband_resources(beam_id=1, request_params=request_params)

    assert output[1]["db_bufsz"] == db_bufsz
    assert output[1]["db_nbufs"] == num_of_buffers

    assert output[1]["wb_bufsz"] == wb_bufsz
    assert output[1]["wb_nbufs"] == num_of_buffers
