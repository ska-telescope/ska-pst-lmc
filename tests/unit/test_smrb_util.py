# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the SMRB utility methods."""


import pytest

from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


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
