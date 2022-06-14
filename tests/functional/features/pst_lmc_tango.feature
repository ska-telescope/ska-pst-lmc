# -*- coding: utf-8 -*-
#
# This file is part of the SKA Low MCCS project
#
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

Feature: PST LMC Tango

Background:
    Given BEAM is running
    And SMRB is running
    And RECV is running

Scenario: BEAM turns on SMRB
    Given BEAM is ready to receive On command
    And SMRB is ready to receive On command
    When BEAM receives On command
    Then SMRB is put into OFFLINE admin state
    And SMRB is put into EMPTY observation state

Scenario: BEAM turns on RECV
    Given BEAM is ready to receive On command
    And RECV is ready to receive On command
    When BEAM receives On command
    Then RECV is put into ONLINE admin state
    And RECV is put into EMPTY observation state

Scenario: BEAM assigns resources in SMRB
    Given BEAM is in EMPTY observation state
    When BEAM receives AssignResources command
    Then SMRB is put into RESOURCING then IDLE observation state

Scenario: BEAM assigns resources in RECV
    Given BEAM is in EMPTY observation state
    When BEAM receives AssignResources command
    Then RECV is put into RESOURCING then IDLE observation state
