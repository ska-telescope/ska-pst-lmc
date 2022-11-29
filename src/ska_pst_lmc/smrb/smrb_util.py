# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of SMRB."""

__all__ = [
    "generate_data_key",
    "generate_weights_key",
    "calculate_smrb_subband_resources",
]

from typing import Any, Dict

from ska_pst_lmc.band.band_config import get_frequency_band_config

SIZE_OF_FLOAT32_IN_BYTES = 4
BITS_PER_BYTE = 8

DATA_KEY_SUFFIX: int = 0
WEIGHTS_KEY_SUFFIX: int = 2

HEADER_BUFFER_NBUFS: int = 8
HEADER_BUFFER_BUFSZ: int = 16384

WEIGHTS_NBITS = 16


def generate_data_key(beam_id: int, subband_id: int) -> str:
    """Generate a data header key.

    The format of this is a string of 4 chars long. The first two
    chars is the beam_id represented in hexadecimal with left zero
    padding, the next is subband_id, and finally a suffix of 0.

    :param beam_id: the beam_id that this LMC component is for.
    :param subband_id: the id of the subband to generate the key for.
    :returns: the encoded key to be used for the data header ringbuffer.
    """
    return "{0:02x}{1}{2}".format(beam_id, subband_id, DATA_KEY_SUFFIX)


def generate_weights_key(beam_id: int, subband_id: int) -> str:
    """Generate a weights header key.

    The format of this is a string of 4 chars long. The first two
    chars is the beam_id represented in hexadecimal with left zero
    padding, the next is subband_id, and finally a suffix of 2.

    NOTE: the weights key is 2 more than the data key, needed because
    SMRB.CORE has 2 keys for each ring buffer.

    :param beam_id: the beam_id that this LMC component is for.
    :param subband_id: the id of the subband to generate the key for.
    :returns: the encoded key to be used for the data header ringbuffer.
    """
    return "{0:02x}{1}{2}".format(beam_id, subband_id, WEIGHTS_KEY_SUFFIX)


def calculate_smrb_subband_resources(beam_id: int, request_params: Dict[str, Any]) -> Dict[int, dict]:
    """Calculate the ring buffer (RB) resources from request.

    This is a common method used to calculate the keys, number of buffers, and
    the size of buffers for each subband required for a scan.

    :param beam_id: the numerical id of the beam that this RB is for.
    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for SMRB are extracted within
        this method.
    :returns: a dict of dicts, with the top level key being the subband id, while
        the second level is the specific parameters. An example would response
        is as follows::

            {
                1: {
                    'data_key': "a000",
                    'weights_key': "a010",
                    'hb_nbufs': 8,
                    'hb_bufsz': 4096,
                    'db_nbufs': 8,
                    'db_bufsz': 1048576,
                    'wb_nbufs': 8,
                    'wb_bufsz': 8192,
                }
            }

    """
    frequency_band_config = get_frequency_band_config(**request_params)
    packet_nchan = frequency_band_config["packet_nchan"]
    packets_per_buffer = frequency_band_config["packets_per_buffer"]
    num_of_buffers = frequency_band_config["num_of_buffers"]

    obsnchan = request_params["num_frequency_channels"]
    obsnpol = request_params["num_of_polarizations"]
    # this is 2 * num bits per dimension (real + complex)
    nbits = request_params["bits_per_sample"]
    udp_nsamp = request_params["udp_nsamp"]
    wt_nsamp = request_params["wt_nsamp"]
    # this should be 1 as udp_nsamp should equal wt_nsamp
    wt_nweight = udp_nsamp // wt_nsamp

    data_buffer_resolution = obsnchan * obsnpol * nbits // BITS_PER_BYTE * udp_nsamp
    # this should be efficitvely 2 * obsnchan as WEIGHTS_NBITS is 16


    weights_buffer_resolution = (
        obsnchan // packet_nchan * SIZE_OF_FLOAT32_IN_BYTES
    ) + obsnchan * WEIGHTS_NBITS // BITS_PER_BYTE * wt_nweight

    return {
        1: {
            "data_key": generate_data_key(beam_id=beam_id, subband_id=1),
            "weights_key": generate_weights_key(beam_id=beam_id, subband_id=1),
            "hb_nbufs": HEADER_BUFFER_NBUFS,
            "hb_bufsz": HEADER_BUFFER_BUFSZ,
            "db_nbufs": num_of_buffers,
            "db_bufsz": packets_per_buffer * data_buffer_resolution,
            "wb_nbufs": num_of_buffers,
            "wb_bufsz": packets_per_buffer * weights_buffer_resolution,
        }
    }
