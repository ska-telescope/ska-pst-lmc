# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of RECV."""

__all__ = [
    "calculate_receive_subband_resources",
]

from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key

MEGA_HERTZ = 1e6
"""CSP sends values in SI units, including frequencies as Hz."""

NUM_DIMENSIONS = 2
"""While PST can handle real and complex data, SKA is using only complex."""


def calculate_receive_subband_resources(beam_id: int, request_params: dict) -> dict:
    """Calculate the RECV resources from request.

    This is a common method to map a CSP JSON request to the appropriate
    RECV.CORE parameters. It is also used to calculate the specific subband
    resources.

    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for SMRB are extracted within
        this method.
    :returns: a dict of dicts, with the top level key being the subband id, while
        the second level is the specific parameters. An example would response
        is as follows::
        TODO - update docs
    """
    # will build up request via unit tests
    # "bits_per_sample": 32,  # this is NDIM * NBITS -> ndim == 2
    # "oversampling_ratio": [8, 7],  # ovrsamp
    # # tsamp - this is calculated

    # // sampling time, inferred from the bandwidth, nchan and oversample
    # float tsamp                 = 18;
    # // oversampling rate
    # repeated uint64 ovrsamp     = 19;
    # // number of subbands
    # uint64 nsubband             = 20;

    nchan = request_params["num_frequency_channels"]
    oversampling_ratio = request_params["oversampling_ratio"]
    bandwidth = request_params["total_bandwidth"]
    tsamp = (
        1.0 / (bandwidth / nchan * oversampling_ratio[0] / oversampling_ratio[1]) / 1_000_000
    )  # need this in samples / microsecs

    return {
        "common": {
            "nchan": nchan,
            "nsubband": 1,
            "udp_nsamp": request_params["udp_nsamp"],
            "wt_nsamp": request_params["wt_nsamp"],
            "udp_nchan": request_params["udp_nchan"],
            "frequency": request_params["centre_frequency"] / MEGA_HERTZ,
            "bandwidth": bandwidth / MEGA_HERTZ,
            "frontend": request_params["timing_beam_id"],
            "fd_poln": request_params["feed_polarization"],
            "fn_hand": request_params["feed_handedness"],
            "fn_sang": request_params["feed_angle"],
            "fd_mode": request_params["feed_tracking_mode"],
            "fa_req": request_params["feed_position_angle"],
            "nant": len(request_params["receptors"]),
            "antennnas": request_params["receptors"],
            "ant_weights": request_params["receptor_weights"],
            "npol": request_params["num_of_polarizations"],
            "nbits": request_params["bits_per_sample"] // NUM_DIMENSIONS,
            "ndim": NUM_DIMENSIONS,
            "tsamp": tsamp,
            "ovrsamp": oversampling_ratio,
        },
        "subbands": {
            1: {
                "data_key": generate_data_key(beam_id=beam_id, subband_id=1),
                "weights_key": generate_weights_key(beam_id=beam_id, subband_id=1),
                "bandwidth": bandwidth / MEGA_HERTZ,
                "nchan": nchan,
                "frequency": request_params["centre_frequency"] / MEGA_HERTZ,
                "chan_range": [1, nchan],
                "chan_out_range": [1, nchan],
                "nchan_out": nchan,
                "bandwidth_out": bandwidth / MEGA_HERTZ,
                "frequency_out": request_params["centre_frequency"] / MEGA_HERTZ,
            },
        },
    }
