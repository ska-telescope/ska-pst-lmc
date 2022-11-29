# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of RECV."""

__all__ = [
    "calculate_receive_common_resources",
    "calculate_receive_subband_resources",
]

from typing import Any, Dict, List, Optional

from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key

MEGA_HERTZ = 1_000_000
"""CSP sends values in SI units, including frequencies as Hz."""

NUM_DIMENSIONS = 2
"""While PST can handle real and complex data, SKA is using only complex."""

DEFAULT_COORD_MODE = "J2000"
"""Default coordinate mode.

Currently only J2000 is supported but in future other modes coulde be supported.
"""

DEFAULT_EQUINOX = 2000.0
"""Default equinox for equitorial/J2000 coordinate mode."""

DEFAULT_TRACKING_MODE = "TRACK"
"""Default tracking mode.

Currently only TRACK is supported but other modes could be supported in the future.
"""


def get_udp_format(frequency_band: Optional[str] = None, **kwargs: Any) -> str:
    """Get UDP_FORMAT to be used in processing."""
    from ska_pst_lmc.band.band_config import get_frequency_band_config

    return get_frequency_band_config(frequency_band=frequency_band)["udp_format"]


def generate_recv_scan_request(
    request_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Map the LMC configure request to what is needed by RECV.CORE.

    This is a common method to map a CSP JSON configure scan request
    to the appropriate RECV.CORE parameters.

    :param request_params: a dictionary of request parameters that is
        used to configure PST for a scan.
    :returns: the RECV.CORE parameters to be used in the gRPC request.
    """
    result = {
        "activation_time": request_params["activation_time"],
        "observer": request_params["observer_id"],
        "projid": request_params["project_id"],
        "pnt_id": request_params["pointing_id"],
        "subarray_id": request_params["subarray_id"],
        "source": request_params["source"],
        "itrf": ",".join(map(str, request_params["itrf"])),
        "coord_md": DEFAULT_COORD_MODE,
        "equinox": str(request_params["coordinates"].get("equinox", DEFAULT_EQUINOX)),
        "stt_crd1": request_params["coordinates"]["ra"],
        "stt_crd2": request_params["coordinates"]["dec"],
        "trk_mode": DEFAULT_TRACKING_MODE,
        "scanlen_max": int(request_params["max_scan_length"]),
    }

    if "test_vector_id" in request_params:
        result["test_vector"] = request_params["test_vector_id"]

    return result


def calculate_receive_common_resources(
    request_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculate the RECV common resources.

    This method has been refactored out of `calculate_receive_subband_resources`
    as there are parameters that are calculated that can be reused in other
    areas such as the `bytes_per_second` used in DSP.

    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for SMRB are extracted within
        this method.
    """
    udp_format = get_udp_format(**request_params)

    nchan = request_params["num_frequency_channels"]
    npol = request_params["num_of_polarizations"]
    nbits = request_params["bits_per_sample"] // NUM_DIMENSIONS
    oversampling_ratio = request_params["oversampling_ratio"]
    bandwidth = request_params["total_bandwidth"]
    bandwidth_mhz = bandwidth / MEGA_HERTZ

    tsamp = 1 / (
        bandwidth_mhz / nchan * oversampling_ratio[0] / oversampling_ratio[1]
    )  # need this in samples / microsecs

    bytes_per_second = nchan * npol * nbits * NUM_DIMENSIONS / 8 * 1_000_000 / tsamp

    return {
        "nchan": nchan,
        "nsubband": 1,
        "udp_nsamp": request_params["udp_nsamp"],
        "wt_nsamp": request_params["wt_nsamp"],
        "udp_nchan": request_params["udp_nchan"],
        "frequency": request_params["centre_frequency"] / MEGA_HERTZ,
        "bandwidth": bandwidth_mhz,
        "frontend": request_params["timing_beam_id"],
        "fd_poln": request_params["feed_polarization"],
        "fd_hand": request_params["feed_handedness"],
        "fd_sang": request_params["feed_angle"],
        "fd_mode": request_params["feed_tracking_mode"],
        "fa_req": request_params["feed_position_angle"],
        "nant": len(request_params["receptors"]),
        "antennas": ",".join(request_params["receptors"]),
        "ant_weights": ",".join(map(str, request_params["receptor_weights"])),
        "npol": npol,
        "nbits": nbits,
        "ndim": NUM_DIMENSIONS,
        "tsamp": tsamp,
        "ovrsamp": "/".join(map(str, oversampling_ratio)),
        "udp_format": udp_format,
        "bytes_per_second": bytes_per_second,
    }


def calculate_receive_subband_resources(
    beam_id: int,
    request_params: Dict[str, Any],
    data_host: str,
    subband_udp_ports: List[int],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Calculate the RECV resources for all subbands from request.

    This is a common method to map a CSP JSON request to the appropriate
    RECV.CORE parameters. It is also used to calculate the specific subband
    resources.

    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for RECV are extracted within
        this method.
    :type request_paras: Dict[str, Any]
    :param data_host: the data host IP in which the data will be received on.
    :type data_host: str
    :param subband_udp_ports: a list of UDP ports for each of the subbands.
        Max length is 4 given there is a maximum of 4 subbands.
    :type subband_udp_ports: List[int]

    :returns: a dict of dicts, with "common" and "subbands" as the top level
        keys.  The `common` values comes from the :py:func:`calculate_receive_common_resources`
        function.  The `subbands` is a dict of dicts with subband ids as the keys, while
        the second level is the specific parameters. An example would response
        is as follows::

            {
                "common": {
                    "nchan": nchan,
                    "nsubband": 1,
                    ...
                },
                "subbands": {
                    1: {
                        "data_key": "a000",
                        "weights_key": "a010",
                        ...
                    }
                }
            }

    """
    nchan = request_params["num_frequency_channels"]
    bandwidth = request_params["total_bandwidth"]

    return {
        "common": calculate_receive_common_resources(request_params),
        "subbands": {
            1: {
                "data_key": generate_data_key(beam_id=beam_id, subband_id=1),
                "weights_key": generate_weights_key(beam_id=beam_id, subband_id=1),
                "bandwidth": bandwidth / MEGA_HERTZ,
                "nchan": nchan,
                "frequency": request_params["centre_frequency"] / MEGA_HERTZ,
                "start_channel": 0,
                "end_channel": nchan,  # using exclusive range
                "start_channel_out": 0,
                "end_channel_out": nchan,  # using exclusive range
                "nchan_out": nchan,
                "bandwidth_out": bandwidth / MEGA_HERTZ,
                "frequency_out": request_params["centre_frequency"] / MEGA_HERTZ,
                "data_host": data_host,
                "data_port": subband_udp_ports[0],
            },
        },
    }
