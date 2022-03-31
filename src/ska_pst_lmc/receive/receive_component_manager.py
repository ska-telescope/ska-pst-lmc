# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the base PST component manager."""

### TODO - expose the properties that the RECV device needs
### - add SIMULATION mode - this will be extracted out later
###     - this will need to update the stats on given period

from __future__ import annotations
import logging
from typing import Any, Callable, List
from ska_pst_lmc.component import PstComponentManager
from ska_tango_base.base.component_manager import CommunicationStatus

class PstReceiveComponentManager(PstComponentManager):

    def __init__(self: PstReceiveComponentManager,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable[[bool], None],
        *args: Any,
        **kwargs: Any
    ):
        super().__init__(logger, communication_state_callback, component_state_callback, *args, **kwargs)


    @property
    def received_rate(self: PstReceiveComponentManager) -> float:
        """Get the current data receive rate from the CBF interface.

        :returns: current data receive rate from the CBF interface in Gb/s.
        :rtype: float
        """
        return 0.0

    @property
    def received_data(self: PstReceiveComponentManager) -> int:
        """Get the total amount of data received from CBF interface for current scan.

        :returns: total amount of data received from CBF interface for current scan in Bytes
        :rtype: int
        """
        return 0

    @property
    def dropped_rate(self: PstReceiveComponentManager) -> float:
        """Get the current rate of CBF ingest data being dropped or lost by the receiving proces.

        :returns: current rate of CBF ingest data being dropped or lost in MB/s.
        :rtype: float
        """
        return 0.0


    @property
    def dropped(self: PstReceiveComponentManager) -> int:
        """Get the total number of bytes dropped in the current scan.

        :returns: total number of bytes dropped in the current scan in Bytes.
        :rtype: int
        """
        return 0

    @property
    def misordered_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of packets received out of order in the current scan.

        :returns: total number of packets received out of order in the current scan.
        :rtype: int
        """
        return 0


    @property
    def malformed_packets(self: PstReceiveComponentManager) -> int:
        """Get the total number of malformed packets received during the current scan.

        :returns: total number of malformed packets received during the current scan.
        :rtype: int
        """
        return 0

    @property
    def relative_weight(self: PstReceiveComponentManager) -> float:
        """Get the time averages of all relative weights for the current scan.

        :returns: time average of all relative weights for the current scan.
        :rtype: float
        """
        return 0.0

    @property
    def relative_weights(self: PstReceiveComponentManager) -> List[float]:
        """Get the time average of relative weights for each channel in the current scan.

        :returns: time average of relative weights for each channel in the current scan.
        :rtype: list(float)
        """
        return [0.0]
