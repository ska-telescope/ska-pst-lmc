# -*- coding: utf-8 -*-
#
# This file is part of the SKA Low MCCS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

Feature: SMRB Component

Background:
    Given SMRB.MNGT is running
    And SMRB.CORE is running

Scenario: SMRB.MNGT can communicate with SMRB.CORE
    Given SMRB.MNGT is not ready to receive On command
    When SMRB.MNGT receives On command
    Then SMRB.MNGT is communicating with SMRB.CORE

Scenario: SMRB.MNGT can assign different subbands in SMRB.CORE
    Given SMRB.MNGT is ready to receive AssignResources command
    When SMRB.MNGT receives AssignResources command with "sub_bands"
    Then only SMRC.CORE "sub_bands" are assigned resources

    Examples:
        | sub_bands  |
        | 1          |
        | 1, 2       |
        | 1, 3, 4    |
        | 2, 3, 4    |
        | 1, 2, 3, 4 |
