# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
"""Release information for SKA PST LMC Python Package."""
import sys
from typing import Union

NAME = """ska_pst_lmc"""
VERSION = "0.6.1"
VERSION_INFO = VERSION.split(".")
DESCRIPTION = """A set of PST LMC tango devices for the SKA Low and Mid Telescopes."""
AUTHOR = "William Gauvin"
AUTHOR_EMAIL = "wgauvin@swin.edu.au"
URL = """https://gitlab.com/ska-telescope/pst/ska-pst-lmc"""
LICENSE = """BSD-3-Clause"""
COPYRIGHT = "Swinburne University of Technology"


def get_release_info(clsname: Union[str, None] = None) -> str:
    """Return a formated release info string.

    :param clsname: optional name of class to add to the info
    :type clsname: string

    :return: string
    """
    rmod = sys.modules[__name__]
    info = ", ".join((rmod.NAME, rmod.VERSION, rmod.DESCRIPTION))
    if clsname is None:
        return info
    return ", ".join((clsname, info))
