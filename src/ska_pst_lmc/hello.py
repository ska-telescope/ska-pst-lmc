# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Package for the simple Hello class.

This package is used to prove we have our development practices in place.
"""

from __future__ import annotations

from typing import Any, Union

__all__ = ["Hello"]


class Hello:
    """Simple Hello World class.

    This class is used to prove that this project can be used for development.

    :param name: The person/object to say hello to, defaults to None
    :type name: str
    """

    def __init__(self: Hello, *args: Any, name: Union[str, None] = None, **kwargs: dict) -> None:
        """Initialise callable object.

        :param name: the name to say hello to, defaults to "World"
        :type name: str
        """
        self.name = name or "World"

    def __call__(self: Hello) -> None:
        """Execute the ``Hello`` object."""
        print(f"Hello {self.name}!")


def main(*args: Any) -> None:
    """Execute hello world method."""
    import argparse

    parser = argparse.ArgumentParser(description="Simple Hello World")
    parser.add_argument("name", nargs="?")

    args = parser.parse_args(*args)

    obj = Hello(**vars(args))
    obj()


if __name__ == "__main__":
    main()
