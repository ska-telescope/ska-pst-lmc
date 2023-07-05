# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""
This module provides configuration for the different frequency bands.

The configuration in here is used by the SMRB and RECV utils to ensure that the ring buffers as set up
correctly and that the header record by RECV.CORE will have the correct udp_format.
"""

__all__ = ["get_frequency_band_config"]

from typing import Any, Dict, Optional

LOW_BAND_CONFIG = {
    "udp_format": "LowPST",
    "packet_nchan": 24,
    "packet_nsamp": 32,
    "packets_per_buffer": 16,
    "num_of_buffers": 64,
}

COMMON_MID_CONFIG = {
    "packet_nchan": 185,
    "packet_nsamp": 4,
}

MID_BAND_CONFIG = {
    "1": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand1",
        "packets_per_buffer": 1024,
        "num_of_buffers": 128,
    },
    "2": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand2",
        "packets_per_buffer": 1024,
        "num_of_buffers": 128,
    },
    "3": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand3",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
    "4": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand4",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
    "5a": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand5",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
    "5b": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand5",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
}


def get_frequency_band_config(frequency_band: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Get the configuration specific for a frequency band.

    This will return the configuration that is specific to a frequency band.
    The standard for SKA is that if the frequency_band is only set or is "low"
    then it corresponds to the Low telescope, which has only one band. Frequency
    bands of 1, 2, 3, 4, 5a, or 5b will return specific configuration.

    The keys that are returned are:
        * udp_format
        * packet_nchan
        * packet_nsamp
        * packets_per_buffer
        * num_of_buffers

    An example output is as follows::

        {
            "udp_format": "LowPST",
            "packet_nchan": 24,
            "packet_nsamp": 32,
            "packets_per_buffer": 16,
            "num_of_buffers": 64,
        }

    :param frequency_band: the frequency band to get configuration for, defaults to None
    :type frequency_band: Optional[str], optional
    :return: a dictionary of configuration for the frequency band.
    :rtype: Dict[str, Any]
    """
    if frequency_band is None or frequency_band == "low":
        return LOW_BAND_CONFIG

    return MID_BAND_CONFIG[frequency_band]
