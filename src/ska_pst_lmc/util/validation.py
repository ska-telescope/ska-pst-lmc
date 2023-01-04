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


def validate(config: dict, strictness: Strictness = Strictness.Strict) -> dict:
    """Validate a :py:class:`dict` against the CSP config schema.

    :param config: the object that needs to be validated.
    :type config: dict
    :param strictness: used to handle level of Schema strictness.
    :type strictness: :py:class:`Strictness`
    :returns: an updated dictionary based on :py:meth:`schema.validate`,
        which includes the default values.
    :raises: :py:class:`ValueError` exception if there is an exception in validation.
    """
    from schema import Schema, SchemaError
    from ska_telmodel.csp import get_csp_config_schema

    try:
        version: str = config["interface"]
    except KeyError:
        raise ValueError("Version not found. It should be >= 2.3")

    (major, minor) = _split_interface_version(version)

    if (major, minor) <= (2, 2):
        raise ValueError(f"Version {major}.{minor} should be >= 2.3")

    # get the CSP schema
    schema: Schema = get_csp_config_schema(version=version, strict=(strictness == Strictness.Strict))

    try:
        return schema.validate(config)
    except SchemaError as e:
        message = f"Validation {e}"
        raise ValueError(message) from e
