# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV utility methods."""


from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources
from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


def test_calculate_receive_subband_resources(
    beam_id: int,
    assign_resources_request: dict,
) -> None:
    """Test that the correct RECV subband resources request is created."""
    actual = calculate_receive_subband_resources(beam_id=beam_id, request_params=assign_resources_request)

    assert "common" in actual
    assert "subbands" in actual
    assert 1 in actual["subbands"]

    actual_common = actual["common"]

    assert actual_common["nsubband"] == 1

    assert actual_common["udp_nsamp"] == assign_resources_request["udp_nsamp"]
    assert actual_common["wt_nsamp"] == assign_resources_request["wt_nsamp"]
    assert actual_common["udp_nchan"] == assign_resources_request["udp_nchan"]
    assert actual_common["frequency"] == assign_resources_request["centre_frequency"] / 1e6
    assert actual_common["bandwidth"] == assign_resources_request["total_bandwidth"] / 1e6
    assert actual_common["nchan"] == assign_resources_request["num_frequency_channels"]
    assert actual_common["frontend"] == assign_resources_request["timing_beam_id"]
    assert actual_common["fd_poln"] == assign_resources_request["feed_polarization"]
    assert actual_common["fn_hand"] == assign_resources_request["feed_handedness"]
    assert actual_common["fn_sang"] == assign_resources_request["feed_angle"]
    assert actual_common["fd_mode"] == assign_resources_request["feed_tracking_mode"]
    assert actual_common["fa_req"] == assign_resources_request["feed_position_angle"]
    assert actual_common["nant"] == len(assign_resources_request["receptors"])
    assert actual_common["antennnas"] == assign_resources_request["receptors"]
    assert actual_common["ant_weights"] == assign_resources_request["receptor_weights"]
    assert actual_common["npol"] == assign_resources_request["num_of_polarizations"]
    assert actual_common["nbits"] == assign_resources_request["bits_per_sample"] // 2
    assert actual_common["ndim"] == 2
    assert actual_common["ovrsamp"] == assign_resources_request["oversampling_ratio"]

    oversample_ratio = assign_resources_request["oversampling_ratio"]
    expected_tsamp = (
        1.0
        / (
            assign_resources_request["total_bandwidth"]
            / assign_resources_request["num_frequency_channels"]
            * oversample_ratio[0]
            / oversample_ratio[1]
        )
        / 1_000_000
    )  # this in in µsecs
    assert abs(actual_common["tsamp"] - expected_tsamp) < 1e-6

    actual_subband_1 = actual["subbands"][1]

    assert actual_subband_1["data_key"] == generate_data_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["weights_key"] == generate_weights_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["bandwidth"] == actual_common["bandwidth"]
    assert actual_subband_1["nchan"] == actual_common["nchan"]
    assert actual_subband_1["frequency"] == actual_common["frequency"]
    assert actual_subband_1["chan_range"] == [1, assign_resources_request["num_frequency_channels"]]
    assert actual_subband_1["bandwidth_out"] == actual_common["bandwidth"]
    assert actual_subband_1["nchan_out"] == actual_common["nchan"]
    assert actual_subband_1["frequency_out"] == actual_common["frequency"]
    assert actual_subband_1["chan_out_range"] == [1, assign_resources_request["num_frequency_channels"]]
