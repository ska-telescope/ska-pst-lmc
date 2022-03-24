# -*- coding: utf-8 -*-
#
# This file is part of the PstBeam project
#
# Swinburne University of Technology
#
# Distributed under the terms of the none license.
# See LICENSE.txt for more info.

"""This module is used as a utility module for dealing with configuration."""

from __future__ import annotations

from typing import Any


class Configuration(object):
    """Configuration.

    This class represents a PST-LMC configuration that is
    sent from the CSP. It is a generic object that is
    able to validate itself against the `ska-telmodel`
    schema for PST.

    Creating instances of these from a JSON encoded string
    should be done via the `Configration.from_json()` method.
    To convert the object to a JSON encoded string should
    be throught the `to_json()` method.
    """

    def __init__(self: Configuration, values: dict) -> None:
        """Initialise object with values.

        :param values: a dict of values that the Configuration object
            represents.
        :type values: dict
        """
        from copy import deepcopy

        if values is None or len(values) == 0:
            raise ValueError("Parameter 'values' must not be empty")

        self._values = deepcopy(values)

    def __getattr__(self: Configuration, name: str) -> Any:
        """Get attribute from configuration.

        Allows calling `cfg.foo` to get the value of foo.

        :param name: name of parameter.
        :type name: str
        :rtype: Any
        """
        return self._values[name]

    def __setattr__(self: Configuration, name: str, value: Any) -> None:
        """Set value of configuration item.

        :param name: name of configuration item to set.
        :type name: str
        :param value: the value of the configuration item to set.
        :type value: Any
        """
        if name == "_values":
            self.__dict__["_values"] = value
        else:
            self._values[name] = value

    def __getitem__(self: Configuration, name: str) -> Any:
        """Get value of configuration item.

        :param name: name of configuration item to get.
        :type name: str
        :returns: the value of the configuration item.
        :rtype: Any
        :raises: :py:class:`KeyError` if item does not exist.
        """
        return self._values[name]

    def __delitem__(self: Configuration, name: str) -> None:
        """Delete configuration item.

        :param name: name of configuration item to delete.
        :type name: str
        """
        del self._values[name]

    def __setitem__(self: Configuration, name: str, value: Any) -> None:
        """Set item on configuration.

        :param name: name of the configuration item.
        :type name: str
        :param value: value of the configuration item.
        :type name: Any
        """
        self._values[name] = value

    def __len__(self: Configuration) -> int:
        """Get the length of internal dict."""
        return len(self._values)

    def keys(self: Configuration) -> Any:
        """Get the keys from internal dict."""
        return self._values.keys()

    def values(self: Configuration) -> Any:
        """Get the values from internal dict."""
        return self._values.values()

    def items(self: Configuration) -> Any:
        """Get the items from internal dict."""
        return self._values.items()

    @staticmethod
    def from_json(json_str: str) -> Configuration:
        """Create Configuration class from JSON string.

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

        from .validation import validate

        obj = json.loads(json_str)

        obj = validate(obj)

        return Configuration(values=obj)

    def to_json(self: Configuration) -> str:
        """Serialise the Configuration object to a JSON string.

        This is a helper method to serialised the configuration
        object to a JSON string. This is effectively

        .. code-block: python

            json.dumps(self._values)

        :returns: a JSON encoded string.
        :rtype: str
        """
        import json

        return json.dumps(self._values)
