# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of SMRB."""

from typing import Dict

DATA_KEY_SUFFIX: int = 0
WEIGHTS_KEY_SUFFIX: int = 2

HEADER_BUFFER_NBUFS: int = 8
HEADER_BUFFER_BUFSZ: int = 4096

DATA_BUFFER_NBUFS: int = 8
DATA_BUFFER_BUFSZ_FACTOR: int = 180

WEIGHTS_NBITS = 16
WEIGHTS_BUFFER_NBUFS: int = 8
WEIGHTS_BUFFER_BUFSZ_FACTOR: int = 180


def calculate_smrb_subband_resources(beam_id: int, request_params: dict) -> Dict[int, dict]:
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
    obsnchan = request_params["num_frequency_channels"]
    obsnpol = request_params["num_of_polarizations"]
    # this is 2 * num bits per dimension (real + complex)
    nbits = request_params["bits_per_sample"]
    udp_nsamp = request_params["udp_nsamp"]
    wt_nsamp = request_params["wt_nsamp"]
    # this should be 1 as udp_nsamp should equal wt_nsamp
    wt_nweight = udp_nsamp // wt_nsamp

    data_buffer_resolution = obsnchan * obsnpol * nbits // 8 * udp_nsamp
    # this should be efficitvely 2 * obsnchan as WEIGHTS_NBITS is 16
    weights_buffer_resolution = obsnchan * WEIGHTS_NBITS // 8 * wt_nweight

    return {
        1: {
            "data_key": "{0:02x}{1}{2}".format(beam_id, 1, DATA_KEY_SUFFIX),
            "weights_key": "{0:02x}{1}{2}".format(beam_id, 1, WEIGHTS_KEY_SUFFIX),
            "hb_nbufs": HEADER_BUFFER_NBUFS,
            "hb_bufsz": HEADER_BUFFER_BUFSZ,
            "db_nbufs": DATA_BUFFER_NBUFS,
            "db_bufsz": DATA_BUFFER_BUFSZ_FACTOR * data_buffer_resolution,
            "wb_nbufs": DATA_BUFFER_NBUFS,
            "wb_bufsz": WEIGHTS_BUFFER_BUFSZ_FACTOR * weights_buffer_resolution,
        }
    }
