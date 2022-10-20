# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the RECV utility methods."""

from typing import List

import pytest

from ska_pst_lmc.receive.receive_util import calculate_receive_subband_resources, generate_recv_scan_request
from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


def test_calculate_receive_subband_resources(
    beam_id: int,
    configure_beam_request: dict,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test that the correct RECV subband resources request is created."""
    actual = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )

    assert "common" in actual
    assert "subbands" in actual
    assert 1 in actual["subbands"]

    actual_common = actual["common"]

    assert actual_common["nsubband"] == 1

    assert actual_common["udp_nsamp"] == configure_beam_request["udp_nsamp"]
    assert actual_common["wt_nsamp"] == configure_beam_request["wt_nsamp"]
    assert actual_common["udp_nchan"] == configure_beam_request["udp_nchan"]
    assert actual_common["frequency"] == configure_beam_request["centre_frequency"] / 1e6
    assert actual_common["bandwidth"] == configure_beam_request["total_bandwidth"] / 1e6
    assert actual_common["nchan"] == configure_beam_request["num_frequency_channels"]
    assert actual_common["frontend"] == configure_beam_request["timing_beam_id"]
    assert actual_common["fd_poln"] == configure_beam_request["feed_polarization"]
    assert actual_common["fd_hand"] == configure_beam_request["feed_handedness"]
    assert actual_common["fd_sang"] == configure_beam_request["feed_angle"]
    assert actual_common["fd_mode"] == configure_beam_request["feed_tracking_mode"]
    assert actual_common["fa_req"] == configure_beam_request["feed_position_angle"]
    assert actual_common["nant"] == len(configure_beam_request["receptors"])
    assert actual_common["antennas"] == ",".join(configure_beam_request["receptors"])
    assert actual_common["ant_weights"] == ",".join(map(str, configure_beam_request["receptor_weights"]))
    assert actual_common["npol"] == configure_beam_request["num_of_polarizations"]
    assert actual_common["nbits"] == configure_beam_request["bits_per_sample"] // 2
    assert actual_common["ndim"] == 2
    assert actual_common["ovrsamp"] == "/".join(map(str, configure_beam_request["oversampling_ratio"]))

    actual_subband_1 = actual["subbands"][1]

    assert actual_subband_1["data_key"] == generate_data_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["weights_key"] == generate_weights_key(beam_id=beam_id, subband_id=1)
    assert actual_subband_1["bandwidth"] == actual_common["bandwidth"]
    assert actual_subband_1["nchan"] == actual_common["nchan"]
    assert actual_subband_1["nchan"] == actual_subband_1["end_channel"] - actual_subband_1["start_channel"]
    assert actual_subband_1["frequency"] == actual_common["frequency"]
    assert actual_subband_1["start_channel"] == 0
    assert actual_subband_1["end_channel"] == configure_beam_request["num_frequency_channels"]
    assert actual_subband_1["bandwidth_out"] == actual_common["bandwidth"]
    assert actual_subband_1["nchan_out"] == actual_common["nchan"]
    assert (
        actual_subband_1["nchan_out"]
        == actual_subband_1["end_channel_out"] - actual_subband_1["start_channel_out"]
    )
    assert actual_subband_1["frequency_out"] == actual_common["frequency"]
    assert actual_subband_1["start_channel_out"] == 0
    assert actual_subband_1["end_channel_out"] == configure_beam_request["num_frequency_channels"]


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
    configure_beam_request: dict,
    frequency_band: str,
    expected_udp_format: str,
    recv_network_interface: str,
    recv_udp_port: int,
) -> None:
    """Test that we add the correct udp_format field."""
    configure_beam_request["frequency_band"] = frequency_band
    calculated_resources = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
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
    configure_beam_request: dict,
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
    configure_beam_request["total_bandwidth"] = bandwidth_mhz * 1e6
    configure_beam_request["num_frequency_channels"] = num_frequency_channels
    configure_beam_request["oversampling_ratio"] = oversampling_ratio

    calculated_resources = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
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
    configure_beam_request: dict,
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
    configure_beam_request["total_bandwidth"] = bandwidth_mhz * 1_000_000
    configure_beam_request["num_frequency_channels"] = num_frequency_channels
    configure_beam_request["oversampling_ratio"] = oversampling_ratio
    configure_beam_request["num_of_polarizations"] = npol
    configure_beam_request["bits_per_sample"] = 2 * nbits

    calculated_resources = calculate_receive_subband_resources(
        beam_id=beam_id,
        request_params=configure_beam_request,
        data_host=recv_network_interface,
        data_port=recv_udp_port,
    )

    assert "bytes_per_second" in calculated_resources["common"]
    assert (
        abs(calculated_resources["common"]["bytes_per_second"] - expected_bytes_per_second)
        / expected_bytes_per_second
        < 1e-6
    )


def test_map_configure_request(
    configure_scan_request: dict,
) -> None:
    """Test that the correct RECV subband resources request is created."""
    actual = generate_recv_scan_request(configure_scan_request)

    assert actual["activation_time"] == configure_scan_request["activation_time"]
    assert actual["scan_id"] == configure_scan_request["scan_id"]
    assert actual["observer"] == configure_scan_request["observer_id"]
    assert actual["projid"] == configure_scan_request["project_id"]
    assert actual["pnt_id"] == configure_scan_request["pointing_id"]
    assert actual["subarray_id"] == configure_scan_request["subarray_id"]
    assert actual["source"] == configure_scan_request["source"]
    assert actual["itrf"] == ",".join(map(str, configure_scan_request["itrf"]))
    assert actual["coord_md"] == "J2000"
    assert actual["equinox"] == str(configure_scan_request["coordinates"].get("equinox", "2000.0"))
    assert actual["stt_crd1"] == configure_scan_request["coordinates"]["ra"]
    assert actual["stt_crd2"] == configure_scan_request["coordinates"]["dec"]
    assert actual["trk_mode"] == "TRACK"
    assert actual["scanlen_max"] == int(configure_scan_request["max_scan_length"])
    assert actual["test_vector"] == configure_scan_request["test_vector_id"]


def test_map_configure_request_test_equinox(
    configure_scan_request: dict,
) -> None:
    """Test that the correct RECV subband resources request is created."""
    configure_scan_request["coordinates"]["equinox"] = 2000.0
    actual = generate_recv_scan_request(configure_scan_request)

    assert actual["equinox"] == "2000.0"


def test_map_configure_request_test_vector_not_set(
    configure_scan_request: dict,
) -> None:
    """Test that the correct RECV subband resources request is created."""
    del configure_scan_request["test_vector_id"]
    actual = generate_recv_scan_request(configure_scan_request)

    assert "test_vector" not in actual
