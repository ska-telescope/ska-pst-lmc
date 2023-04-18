# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module defines fixtures specifically for the integration tests."""

import pytest


@pytest.fixture
def monitor_polling_rate_ms() -> int:
    """Get monitor polling rate in milliseconds."""
    return 500
