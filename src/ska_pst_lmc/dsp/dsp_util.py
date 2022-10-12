# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of DSP."""

__all__ = [
    "calculate_dsp_subband_resources",
]

from typing import Any, Dict

from ska_pst_lmc.receive.receive_util import calculate_receive_common_resources
from ska_pst_lmc.smrb.smrb_util import generate_data_key, generate_weights_key


def calculate_dsp_subband_resources(beam_id: int, **kwargs: Any) -> Dict[int, dict]:
    """Calculate the digital signal processing (DSP) resources from request.

    This is a common method to map a CSP JSON request to the appropriate
    DSP parameters. It is also used to calculate the specific subband
    resources.

    This uses the SMRB :py:func:`generate_data_key`, :py:func:`generate_weights_key`
    functions to calculate the keys for the data and weight ring buffers that the DSP
    process will read from.

    :param beam_id: the numerical id of the beam that this DSP request is for.
    :param request_params: a dictionary of request parameters that is used to
        configure PST, the specific parameters for DSP are extracted within
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


def generate_dsp_scan_request(request_params: dict) -> dict:
    recv_common_resources = calculate_receive_common_resources(request_params=request_params)
    bytes_per_second = recv_common_resources["bytes_per_second"]
    scanlen_max = request_params.get("max_scan_length", 0.0)

    return {"bytes_per_second": bytes_per_second, "scanlen_max": scanlen_max}
