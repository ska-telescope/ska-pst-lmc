# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module for providing utility methods of STAT."""

__all__ = [
    "calculate_stat_subband_resources",
]

from typing import Any, Dict

from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key

DEFAULT_PROCESSING_DELAY_MS: int = 5_000
"""The default processing delay, in milliseconds, used to calculate the current statistics."""

DEFAULT_REQ_FREQ_BINS: int = 1024
"""The default number of frequency bins to use when doing a spectragram."""

DEFAULT_REQ_TIME_BINS: int = 1024
"""The default number of time bins to use for spectragram and timeseries data."""

DEFAULT_NUM_REBIN: int = 256
"""The default number of channel bins when rebinning the histogram."""


def calculate_stat_subband_resources(beam_id: int, **kwargs: Any) -> Dict[int, dict]:
    """
    Calculate the statistics (STAT) resources from request.

    This is a common method to map a CSP JSON request to the appropriate
    STAT parameters. It is also used to calculate the specific subband
    resources.

    This uses the SMRB :py:func:`generate_data_key`, :py:func:`generate_weights_key`
    functions to calculate the keys for the data and weight ring buffers that the STAT
    process will read from.

    :param beam_id: the numerical id of the beam that this STAT request is for.
    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for STAT are extracted within
        this method.
    :returns: a dict of dicts, with the top level key being the subband id, while
        the second level is the specific parameters. An example would response
        is as follows::

            {
                1: {
                    'data_key': "a000",
                    'weights_key': "a010",
                }
            }
    """
    return {
        1: {
            "data_key": generate_data_key(beam_id=beam_id, subband_id=1),
            "weights_key": generate_weights_key(beam_id=beam_id, subband_id=1),
        }
    }


def generate_stat_scan_request(request_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the scan request parameters for STAT.

    This maps the given request parameters into a dictionary that will be passed
    to the STAT.CORE application via Protobuf. The parameters stat_processing_delay_ms,
    stat_req_freq_bins, stat_req_time_bins, stat_num_rebin are optional in the
    request parameters but this method will populate them with default values
    (see DEFAULT_PROCESSING_DELAY_MS, DEFAULT_REQ_TIME_BINS,
    DEFAULT_REQ_FREQ_BINS, and DEFAULT_NUM_REBIN respectively)

    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for STAT are extracted within
        this method.
    :returns: a dictionary of specific parameters to send to a STAT.CORE process.
        An example would response is as follows::

            {
                "execution_block_id": "eb-m001-20230712-56789",
                "processing_delay_ms": 5000,
                "stat_req_time_bins": 1024,
                "stat_req_freq_bins": 1024,
                "stat_nrebin": 256,
            }
    """
    return {
        "execution_block_id": request_params["eb_id"],
        "processing_delay_ms": request_params.get("stat_processing_delay_ms", DEFAULT_PROCESSING_DELAY_MS),
        "req_time_bins": request_params.get("stat_req_time_bins", DEFAULT_REQ_TIME_BINS),
        "req_freq_bins": request_params.get("stat_req_freq_bins", DEFAULT_REQ_FREQ_BINS),
        "num_rebin": request_params.get("stat_num_rebin", DEFAULT_NUM_REBIN),
    }
