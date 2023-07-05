# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module provides types and handlers for callbacks."""

from typing import Any, Callable, Optional

__all__ = [
    "Callback",
]

Callback = Optional[Callable[..., Any]]


def wrap_callback(callback: Callback) -> Callable[..., Any]:
    """
    Wrap call back that can take args.

    This method converts an optional callback back to
    a callable by returning a partial function that
    when called checks to see if the supplied callback
    has was `None` or not.

    :param callback: the callback to wrap.
    """
    if callback is not None:
        return callback

    return lambda *args, **kw: None


def callback_safely(callback: Callback, *args: Any, **kwargs: Any) -> Any:
    """
    Call callback safely.

    As a callback could be None this method ensures that it is only called
    when it is not None.  This removes the need for all the code littered with.

    .. code-block:: python

        if callback:
            callback(*args, **kwargs)

    This above code can then be replaced with:

    .. code-block:: python

        callback_safely(callback, *args, **kwargs)
    """
    if callback is not None:
        return callback(*args, **kwargs)
