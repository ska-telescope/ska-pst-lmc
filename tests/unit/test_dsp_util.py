# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the DSP utility methods."""


from ska_pst_lmc.dsp.dsp_util import calculate_dsp_subband_resources
from ska_pst_lmc.receive.receive_util import calculate_receive_common_resources
from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


def test_calculate_receive_subband_resources(
    beam_id: int,
    assign_resources_request: dict,
) -> None:
    """Test that the correct DSP subband resources request is created."""
    actual = calculate_dsp_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
    )

    assert 1 in actual

    actual_subband_1 = actual[1]

    assert actual_subband_1["data_key"] == generate_data_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["weights_key"] == generate_weights_key(beam_id=beam_id, subband_id=1)

    expected_bytes_per_second = calculate_receive_common_resources(assign_resources_request)[
        "bytes_per_second"
    ]
    assert actual_subband_1["bytes_per_second"] == expected_bytes_per_second
