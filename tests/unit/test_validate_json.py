# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains the pytest tests for the validate method."""

from typing import Optional

import pytest
from ska_telmodel.csp.examples import get_csp_config_example
from ska_telmodel.csp.version import CSP_CONFIG_VER2_2, CSP_CONFIG_VERSIONS

from ska_pst_lmc.util import Strictness, validate


def is_valid_combination(version: str, scan: Optional[str]) -> bool:
    """Check if version and scan paramters are valid combinations.

    :param version: version number for the CSP configuration.
    :type version: str
    :param scan: the type of CSP scan to validate.
    :type scan: Optional[str]
    :returns: true or false if not a valid version and scan combination.
    """
    if scan is None or scan not in [
        "pst_beam",
        "pst_scan_pt",
        "pst_scan_ds",
        "pst_scan_ft",
    ]:
        return False

    return version.startswith(CSP_CONFIG_VER2_2)


@pytest.mark.parametrize(
    "version, valid, scan",
    [
        (v, is_valid_combination(v, scan), scan)
        for v in CSP_CONFIG_VERSIONS
        for scan in [
            None,
            "cal_a",
            "science_a",
            "pst_beam",
            "pst_scan_pt",
            "pst_scan_ds",
            "pst_scan_ft",
        ]
    ],
)
def test_only_version_2_2_or_above_accepted(version: str, valid: bool, scan: str) -> None:
    """Test that only version 2.2 of CSP schema is valid.

    Parameterised test that checks different combinations of version and scan valid
    to assert that only version 2.2 above and PST scans are valid.

    :param version: version number for the CSP configuration.
    :type version: str
    :param valid: the expected value of if this a valid version and scan combination.
    :type valid: bool
    :param scan: the type of CSP scan to validate.
    :type scan: str
    """
    try:
        request = get_csp_config_example(version=version, scan=scan)

        if valid:
            validate(request, strictness=Strictness.Strict)
        else:
            with pytest.raises(ValueError, match=r"should be >= 2.2"):
                validate(request, strictness=Strictness.Strict)
    except ValueError:
        pass


def test_should_fail_validation() -> None:
    """Test that invalice CSP JSON/dict fails validation."""
    config = {
        "interface": CSP_CONFIG_VER2_2,
        "pst": {
            "scan": {
                "foo": "bar",
            },
        },
    }

    with pytest.raises(ValueError):
        validate(config)
