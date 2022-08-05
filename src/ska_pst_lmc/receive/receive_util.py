# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing utility methods of RECV."""


def calculate_receive_subband_resources(request_params: dict) -> dict:
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
    return {
        "common": {},
        "subbands": {
            1: {},
        },
    }
