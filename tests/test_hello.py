# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains the pytest tests for the Hello class."""

from pytest import CaptureFixture

from ska_pst_lmc import Hello


def test_hello_has_world_as_default(capsys: CaptureFixture) -> None:
    """
    Test that Hello uses 'World' as default name.

    :param capsys: a fixture to capture the stdout/err for validation.
    :type capsys: `:py:class:: CaptureFixture`
    """
    hello = Hello()

    assert hello.name == "World"
    hello()

    (out, _) = capsys.readouterr()
    assert out == "Hello World!\n"


def test_hello_sets_name(capsys: CaptureFixture) -> None:
    """
    Test that Hello uses supplied name.

    :param capsys: a fixture to capture the stdout/err for validation.
    :type capsys: `:py:class:: CaptureFixture`
    """
    hello = Hello(name="Luke Skywalker")

    assert hello.name == "Luke Skywalker"
    hello()

    (out, _) = capsys.readouterr()
    assert out == "Hello Luke Skywalker!\n"


def test_main(capsys: CaptureFixture) -> None:
    """
    Test the `:py:function:: main` calls `:py:class:: Hello()`.

    :param capsys: a fixture to capture the stdout/err for validation.
    :type capsys: `:py:function:: main`
    """
    from ska_pst_lmc.hello import main

    main(["Bob"])

    (out, _) = capsys.readouterr()
    assert out == "Hello Bob!\n"
