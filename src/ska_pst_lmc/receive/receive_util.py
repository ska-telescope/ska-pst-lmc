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

from typing import Optional

from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key

MEGA_HERTZ = 1e6
"""CSP sends values in SI units, including frequencies as Hz."""

NUM_DIMENSIONS = 2
"""While PST can handle real and complex data, SKA is using only complex."""

LOW_PST = "LowPST"

MID_UDP_FORMATS = {
    "1": "MidPSTBand1",
    "2": "MidPSTBand2",
    "3": "MidPSTBand3",
    "4": "MidPSTBand4",
    "5a": "MidPSTBand5",
    "5b": "MidPSTBand5",
}


def get_udp_format(frequency_band: Optional[str] = None, **kwargs: dict) -> str:
    """Get UDP_FORMAT to be used in processing."""
    if frequency_band in MID_UDP_FORMATS:
        return MID_UDP_FORMATS[frequency_band]

    return LOW_PST


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
    udp_format = get_udp_format(**request_params)

    nchan = request_params["num_frequency_channels"]
    oversampling_ratio = request_params["oversampling_ratio"]
    bandwidth = request_params["total_bandwidth"]
    bandwidth_mhz = bandwidth / MEGA_HERTZ

    tsamp = 1.0 / (
        bandwidth_mhz / nchan * oversampling_ratio[0] / oversampling_ratio[1]
    )  # need this in samples / microsecs

    return {
        "common": {
            "nchan": nchan,
            "nsubband": 1,
            "udp_nsamp": request_params["udp_nsamp"],
            "wt_nsamp": request_params["wt_nsamp"],
            "udp_nchan": request_params["udp_nchan"],
            "frequency": request_params["centre_frequency"] / MEGA_HERTZ,
            "bandwidth": bandwidth_mhz,
            "frontend": request_params["timing_beam_id"],
            "fd_poln": request_params["feed_polarization"],
            "fn_hand": request_params["feed_handedness"],
            "fn_sang": request_params["feed_angle"],
            "fd_mode": request_params["feed_tracking_mode"],
            "fa_req": request_params["feed_position_angle"],
            "nant": len(request_params["receptors"]),
            "antennas": ",".join(request_params["receptors"]),
            "ant_weights": ",".join(map(str, request_params["receptor_weights"])),
            "npol": request_params["num_of_polarizations"],
            "nbits": request_params["bits_per_sample"] // NUM_DIMENSIONS,
            "ndim": NUM_DIMENSIONS,
            "tsamp": tsamp,
            "ovrsamp": "/".join(map(str, oversampling_ratio)),
            "udp_format": udp_format,
        },
        "subbands": {
            1: {
                "data_key": generate_data_key(beam_id=beam_id, subband_id=1),
                "weights_key": generate_weights_key(beam_id=beam_id, subband_id=1),
                "bandwidth": bandwidth / MEGA_HERTZ,
                "nchan": nchan,
                "frequency": request_params["centre_frequency"] / MEGA_HERTZ,
                "start_channel": 0,
                "end_channel": nchan - 1,
                "start_channel_out": 0,
                "end_channel_out": nchan - 1,
                "nchan_out": nchan,
                "bandwidth_out": bandwidth / MEGA_HERTZ,
                "frequency_out": request_params["centre_frequency"] / MEGA_HERTZ,
            },
        },
    }
