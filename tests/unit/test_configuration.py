# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains the pytest tests for the Configuration class."""

import json

import pytest
from ska_telmodel.csp.examples import get_csp_config_example
from ska_telmodel.csp.version import CSP_CONFIG_VER2_2

from ska_pst_lmc.util import Configuration


def test_should_deserialise_valid_json() -> None:
    """Test that Configuration class can deserialise valid JSON."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_2, scan="pst_scan_pt")

    # serialise
    request = json.dumps(example)

    obj = Configuration.from_json(request)

    assert obj is not None


def test_should_add_default_values() -> None:
    """Test that Configuration class populates default values if not present in JSON."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_2, scan="pst_scan_pt")

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
    config = Configuration(values=values)

    result = config.to_json()
    expected = json.dumps(values)

    assert result == expected, f"config.to_json '{result}' not the same as '{expected}'"


def test_should_fail_to_instantiate_if_values_is_none() -> None:
    """Test that Configuration will assert that values can not be None."""
    with pytest.raises(ValueError, match=r"Parameter 'values' must not be empty"):
        Configuration(None)  # type: ignore


def test_should_fail_to_instantiate_if_values_is_empty() -> None:
    """Test that Configuration will assert that values can not be empty."""
    with pytest.raises(ValueError, match=r"Parameter 'values' must not be empty"):
        Configuration({})


def test_get_attributes() -> None:
    """Test being able to get attributes from a Configuration object."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_2, scan="pst_scan_pt")

    obj = Configuration(example)

    assert obj.pst == example["pst"]
    assert obj["pst"] == example["pst"]


def test_set_attributes() -> None:
    """Test being able to set attributes on a Configuration object."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_2, scan="pst_scan_pt")

    # serialise
    request = json.dumps(example)

    obj = Configuration.from_json(request)

    obj["foo"] = "bar"
    obj.cat = "dog"

    assert obj.foo == "bar"
    assert obj["cat"] == "dog"


def test_delete_item() -> None:
    """Test being able to delete an configuration item from a Configuration object."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_2, scan="pst_scan_pt")

    obj = Configuration(example)

    assert "pst" in example
    assert "pst" in obj._values
    assert obj.pst is not None
    assert "pst" in obj.keys()
    del obj["pst"]
    assert "pst" not in obj.keys()


def test_dict_methods() -> None:
    """Test the `dict` magic methods on the Configuration class."""
    example = get_csp_config_example(version=CSP_CONFIG_VER2_2, scan="pst_scan_pt")

    obj = Configuration(example)

    assert len(obj) == len(example)
    assert obj.keys() == example.keys()
    assert [*obj.values()] == [*example.values()]
    assert obj.items() == example.items()

    for k, v in obj.items():
        assert k in example
        assert example[k] == v
