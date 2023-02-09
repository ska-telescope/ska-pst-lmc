# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module is used as a utility module for dealing with validation."""

__all__ = [
    "validate",
    "Strictness",
]

from enum import IntEnum
from typing import Tuple

from schema import Schema


def _split_interface_version(version: str) -> Tuple[int, int]:
    """Extract version number from interface URI.

    :param version: Version string.
    :returns: (major version, minor version) tuple.
    """
    # get the string with the interface semantic version (X.Y)
    version_num = version.rsplit("/", 1)[1]
    (major_version, minor_version) = version_num.split(".")
    return int(major_version), int(minor_version)


class Strictness(IntEnum):
    """Enum for level of strictness for validation."""

    Permissive = (0,)
    Warning = (1,)
    Strict = (2,)


def pst_schema(version: str, strictness: Strictness = Strictness.Permissive) -> Schema:
    """Get the PST.LMC schema.

    This is a scaled down schema from the CSP.LMC schema. If we used
    the CSP schema the `subarray` and `cbf` fields would be need
    """
    from inspect import cleandoc

    from ska_telmodel._common import TMSchema
    from ska_telmodel.csp.schema import get_common_config_schema, get_pst_config_schema

    strict = strictness == Strictness.Strict
    schema = TMSchema.new(
        "PST Configure Scan Schame",
        version,
        strict,
        description=cleandoc(
            """
            Pulsar Timing specific scan configuration parameters.
            This section contains the parameters relevant only for
            PST. This section is forwarded only to PST subelement.
            """
        ),
        as_reference=True,
    )

    schema.add_opt_field("interface", str)
    schema.add_field("common", get_common_config_schema(version, strict))
    schema.add_field("pst", get_pst_config_schema(version, strict))

    return schema


def validate(config: dict, strictness: Strictness = Strictness.Permissive) -> dict:
    """Validate a :py:class:`dict` against the CSP config schema.

    :param config: the object that needs to be validated.
    :type config: dict
    :param strictness: used to handle level of Schema strictness.
    :type strictness: :py:class:`Strictness`
    :returns: an updated dictionary based on :py:meth:`schema.validate`,
        which includes the default values.
    :raises: :py:class:`ValueError` exception if there is an exception in validation.
    """
    from schema import SchemaError

    try:
        version: str = config["interface"]
    except KeyError:
        raise ValueError("Version not found. It should be >= 2.3")

    (major, minor) = _split_interface_version(version)
    if (major, minor) <= (2, 2):
        raise ValueError(f"Version {major}.{minor} should be >= 2.3")

    # get the CSP schema
    schema = pst_schema(version, strictness=strictness)

    try:
        return schema.validate(config)
    except SchemaError as e:
        message = f"Validation {e}"
        raise ValueError(message) from e
