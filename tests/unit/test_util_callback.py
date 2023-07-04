# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""This module contains tests the utility class TimeoutIterator."""

from unittest.mock import MagicMock

from ska_pst_lmc.util.callback import wrap_callback


def test_wrap_callback() -> None:
    """Test wrap_callback."""
    callback = MagicMock()

    wrapped_callback = wrap_callback(callback)
    wrapped_callback()

    callback.assert_called_once()


def test_wrap_callback_handles_none_object() -> None:
    """Test wrap_callback handles callback that is None."""
    output = wrap_callback(None)()
    assert output is None
