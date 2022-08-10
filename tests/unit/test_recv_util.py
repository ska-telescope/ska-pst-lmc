# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV utility methods."""

from typing import List

import pytest

from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources
from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


def test_calculate_receive_subband_resources(
    beam_id: int,
    assign_resources_request: dict,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test that the correct RECV subband resources request is created."""
    actual = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )

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
    assert actual_common["fd_hand"] == assign_resources_request["feed_handedness"]
    assert actual_common["fd_sang"] == assign_resources_request["feed_angle"]
    assert actual_common["fd_mode"] == assign_resources_request["feed_tracking_mode"]
    assert actual_common["fa_req"] == assign_resources_request["feed_position_angle"]
    assert actual_common["nant"] == len(assign_resources_request["receptors"])
    assert actual_common["antennas"] == ",".join(assign_resources_request["receptors"])
    assert actual_common["ant_weights"] == ",".join(map(str, assign_resources_request["receptor_weights"]))
    assert actual_common["npol"] == assign_resources_request["num_of_polarizations"]
    assert actual_common["nbits"] == assign_resources_request["bits_per_sample"] // 2
    assert actual_common["ndim"] == 2
    assert actual_common["ovrsamp"] == "/".join(map(str, assign_resources_request["oversampling_ratio"]))

    actual_subband_1 = actual["subbands"][1]

    assert actual_subband_1["data_key"] == generate_data_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["weights_key"] == generate_weights_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["bandwidth"] == actual_common["bandwidth"]
    assert actual_subband_1["nchan"] == actual_common["nchan"]
    assert (
        actual_subband_1["nchan"] == actual_subband_1["end_channel"] - actual_subband_1["start_channel"] + 1
    )
    assert actual_subband_1["frequency"] == actual_common["frequency"]
    assert actual_subband_1["start_channel"] == 0
    assert actual_subband_1["end_channel"] == assign_resources_request["num_frequency_channels"] - 1
    assert actual_subband_1["bandwidth_out"] == actual_common["bandwidth"]
    assert actual_subband_1["nchan_out"] == actual_common["nchan"]
    assert (
        actual_subband_1["nchan_out"]
        == actual_subband_1["end_channel_out"] - actual_subband_1["start_channel_out"] + 1
    )
    assert actual_subband_1["frequency_out"] == actual_common["frequency"]
    assert actual_subband_1["start_channel_out"] == 0
    assert actual_subband_1["end_channel_out"] == assign_resources_request["num_frequency_channels"] - 1


@pytest.mark.parametrize(
    "frequency_band, expected_udp_format",
    [
        (None, "LowPST"),
        ("1", "MidPSTBand1"),
        ("2", "MidPSTBand2"),
        ("3", "MidPSTBand3"),
        ("4", "MidPSTBand4"),
        ("5a", "MidPSTBand5"),
        ("5b", "MidPSTBand5"),
    ],
)
def test_udp_format_set_in_calculated_resources(
    beam_id: int,
    assign_resources_request: dict,
    frequency_band: str,
    expected_udp_format: str,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test that we add the correct udp_format field."""
    assign_resources_request["frequency_band"] = frequency_band
    calculated_resources = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )

    assert "udp_format" in calculated_resources["common"]
    assert calculated_resources["common"]["udp_format"] == expected_udp_format


@pytest.mark.parametrize(
    "bandwidth_mhz, num_frequency_channels, oversampling_ratio, expected_tsamp",
    [
        (22.22222222, 6144, [4, 3], 207.36),  # LowPST
        (59.6736, 1110, [8, 7], 16.276041667),  # MidPSTBand1
        (198.912, 3700, [8, 7], 16.276041667),  # MidPSTBand2
        (348.096, 6475, [8, 7], 16.276041667),  # MidPSTBand3
        (596.736, 11100, [8, 7], 16.276041667),  # MidPSTBand4
        (626.5728, 11655, [8, 7], 16.276041667),  # MidPSTBand5
    ],
)
def test_recv_util_calc_tsamp(
    beam_id: int,
    assign_resources_request: dict,
    bandwidth_mhz: float,
    num_frequency_channels: int,
    oversampling_ratio: List[int],
    expected_tsamp: float,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test calculations for tsamp.

    Test input values are based on the different telescopes bandwidths.
    Values for these parameterised tests come from the example RECV config
    files in the ska-pst-recv repository.
    """
    assign_resources_request["total_bandwidth"] = bandwidth_mhz * 1e6
    assign_resources_request["num_frequency_channels"] = num_frequency_channels
    assign_resources_request["oversampling_ratio"] = oversampling_ratio

    calculated_resources = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )

    assert "tsamp" in calculated_resources["common"]
    assert abs(calculated_resources["common"]["tsamp"] - expected_tsamp) < 1e-6


@pytest.mark.parametrize(
    "bandwidth_mhz, num_frequency_channels, npol, nbits, oversampling_ratio, expected_bytes_per_second",
    [
        (22.22222222, 6144, 2, 16, [4, 3], 237037037.013),  # LowPST
        (59.6736, 1110, 2, 16, [8, 7], 545587200.000),  # MidPSTBand1
        (198.912, 3700, 2, 16, [8, 7], 1818624000.000),  # MidPSTBand2
        (348.096, 6475, 2, 12, [8, 7], 2386944000.000),  # MidPSTBand3
        (596.736, 11100, 2, 8, [8, 7], 2727936000.000),  # MidPSTBand4
        (626.5728, 11655, 2, 8, [8, 7], 2864332800.000),  # MidPSTBand5
    ],
)
def test_recv_util_calc_bytes_per_seconds(
    beam_id: int,
    assign_resources_request: dict,
    bandwidth_mhz: float,
    num_frequency_channels: int,
    npol: int,
    nbits: int,
    oversampling_ratio: List[int],
    expected_bytes_per_second: float,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test calculations for bytes_per_seconds.

    Test input values are based on the different telescopes bandwidths.
    Values for these parameterised tests come from the example RECV config
    files in the ska-pst-recv repository.
    """
    assign_resources_request["total_bandwidth"] = bandwidth_mhz * 1_000_000
    assign_resources_request["num_frequency_channels"] = num_frequency_channels
    assign_resources_request["oversampling_ratio"] = oversampling_ratio
    assign_resources_request["num_of_polarizations"] = npol
    assign_resources_request["bits_per_sample"] = 2 * nbits

    calculated_resources = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=assign_resources_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )

    assert "bytes_per_second" in calculated_resources["common"]
    assert (
        abs(calculated_resources["common"]["bytes_per_second"] - expected_bytes_per_second)
        / expected_bytes_per_second
        < 1e-6
    )
