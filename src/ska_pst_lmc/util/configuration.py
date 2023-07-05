# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module is used as a utility module for dealing with configuration."""

from __future__ import annotations

from collections import UserDict
from typing import Any


class Configuration(UserDict[str, Any]):
    """
    Configuration.

    This class represents a PST-LMC configuration that is
    sent from the CSP. It is a generic object that is
    able to validate itself against the ``ska-telmodel``
    schema for PST.

    Creating instances of these from a JSON encoded string
    should be done via the `Configration.from_json()` method.
    To convert the object to a JSON encoded string should
    be through the :py:meth:`to_json()` method.
    """

    @staticmethod
    def from_json(json_str: str) -> Configuration:
        """
        Create Configuration class from JSON string.

        Creates an instance of a Configuration class from
        as JSON encoded string. This will also validate that
        the given string matches what is expected, this is
        performed by calling :py:meth:`ska.pst.util.validate`.

        :param json_str: JSON encode string of a configuration object.
        :returns: A Configuration object.
        :rtype: Configuration
        :raises: `ValueError` is not a valid configuration request.
        """
        import json

        from ska_pst_lmc.util.validation import validate

        obj = json.loads(json_str)

        obj = validate(obj)

        return Configuration(**obj)

    def to_json(self: Configuration) -> str:
        """
        Serialise the Configuration object to a JSON string.

        This is a helper method to serialised the configuration
        object to a JSON string. This is effectively

        .. code-block:: python

            json.dumps(self._values)

        :returns: a JSON encoded string.
        :rtype: str
        """
        import json

        return json.dumps(self.data)
