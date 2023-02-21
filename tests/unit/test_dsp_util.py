# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the DSP utility methods."""


from typing import Any, Dict

from ska_pst_lmc.dsp.dsp_util import calculate_dsp_subband_resources, generate_dsp_scan_request
from ska_pst_lmc.receive.receive_util import calculate_receive_packet_resources
from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


def test_calculate_receive_subband_resources(
    beam_id: int,
    configure_beam_request: Dict[str, Any],
) -> None:
    """Test that the correct DSP subband resources request is created."""
    actual = calculate_dsp_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
    )

    assert 1 in actual

    actual_subband_1 = actual[1]

    assert actual_subband_1["data_key"] == generate_data_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["weights_key"] == generate_weights_key(beam_id=beam_id, subband_id=1)


def test_generate_dsp_scan_request(configure_scan_request: Dict[str, Any]) -> None:
    """Test that we generate the correct scan configuration."""
    actual = generate_dsp_scan_request(request_params=configure_scan_request)
    recv_common_resources = calculate_receive_packet_resources(request_params=configure_scan_request)

    assert actual["scanlen_max"] == configure_scan_request["max_scan_length"]
    assert actual["bytes_per_second"] == recv_common_resources["bytes_per_second"]


def test_generate_dsp_scan_request_when_max_scan_length_not_set(
    configure_scan_request: Dict[str, Any]
) -> None:
    """Test that we generate the correct scan configuration when max_scan_length not set."""
    del configure_scan_request["max_scan_length"]
    actual = generate_dsp_scan_request(request_params=configure_scan_request)
    recv_common_resources = calculate_receive_packet_resources(request_params=configure_scan_request)

    assert actual["scanlen_max"] == 0.0
    assert actual["bytes_per_second"] == recv_common_resources["bytes_per_second"]
