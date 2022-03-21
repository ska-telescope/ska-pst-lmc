# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

__all__ = [
    'Hello'
]

class Hello():
    """Simple Hello World class to prove that this project can be used for
    development.

    :param name: The person/object to say hello to, defaults to None
    :type name: str
    """

    def __init__(self, *args, name: str=None, **kwargs):
        self.name = name or "World"

    def __call__(self, *args, **kwargs):
        print(f"Hello {self.name}!")

def main(args=None):
    """Main method to execute hello world.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Simple Hello World");
    parser.add_argument("name", nargs='?');

    args = parser.parse_args(args)

    obj = Hello(**vars(args))
    obj()

if __name__ == '__main__':
    main()
