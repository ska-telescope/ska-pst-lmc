# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains the pytest tests for the Configuration class."""

import json

from ska_telmodel.csp.examples import get_csp_config_example
from ska_telmodel.csp.version import CSP_CONFIG_VER2_3

from ska_pst_lmc.util import Configuration


def test_should_deserialise_valid_json() -> None:
    """Test that Configuration class can deserialise valid JSON."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_3, scan="pst_scan_pt")

    # serialise
    request = json.dumps(example)

    obj = Configuration.from_json(request)

    assert obj is not None


def test_should_add_default_values() -> None:
    """Test that Configuration class populates default values if not present in JSON."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_3, scan="pst_scan_pt")

    try:
        del example["pst"]["scan"]["coordinates"]["equinox"]
    except KeyError:
        pass

    request = json.dumps(example)

    obj = Configuration.from_json(request)

    assert obj["pst"]["scan"]["coordinates"]["equinox"] == 2000.0, "Equinox should have been added as default"


def test_to_json_should_create_json_string() -> None:
    """Test that Configuration serialises itself to a valid JSON string."""
    import json

    values = {"foo": "bar"}
    config = Configuration(values)

    result = config.to_json()
    expected = json.dumps(values)

    assert result == expected, f"config.to_json '{result}' not the same as '{expected}'"


def test_delete_item() -> None:
    """Test being able to delete an configuration item from a Configuration object."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_3, scan="pst_scan_pt")

    obj = Configuration(example)

    assert "pst" in example
    assert "pst" in obj
    assert obj["pst"] is not None
    assert "pst" in obj.keys()
    del obj["pst"]
    assert "pst" not in obj.keys()


def test_dict_methods() -> None:
    """Test the `dict` magic methods on the Configuration class."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_3, scan="pst_scan_pt")

    obj = Configuration(example)

    assert len(obj) == len(example)
    assert obj.keys() == example.keys()
    assert [*obj.values()] == [*example.values()]
    assert obj.items() == example.items()

    for k, v in obj.items():
        assert k in example
        assert example[k] == v
