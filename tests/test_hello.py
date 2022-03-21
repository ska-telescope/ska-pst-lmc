# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

from ska_pst_lmc import Hello

def test_hello_has_world_as_default(capsys):
    hello = Hello()
    
    assert hello.name == 'World'
    hello()

    (out, _) = capsys.readouterr()
    assert out == "Hello World!\n"

def test_hello_sets_name(capsys):
    hello = Hello(name="Luke Skywalker")

    assert hello.name == 'Luke Skywalker'
    hello()

    (out, _) = capsys.readouterr()
    assert out == "Hello Luke Skywalker!\n"

def test_main(capsys):
    from ska_pst_lmc.hello import main

    main(["Bob"])

    (out, _) = capsys.readouterr()
    assert out == "Hello Bob!\n"
