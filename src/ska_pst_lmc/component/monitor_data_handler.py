# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides the base classes for handling monitoring data handling."""

from __future__ import annotations

import threading
from typing import Callable, Dict, Generic, TypeVar

S = TypeVar("S")
T = TypeVar("T")


class MonitorDataStore(Generic[S, T]):
    """Generic monitoring data store that handles subband data.

    This is an abstract class that other classes should extend to allow
    following for a contract about how to handle subband data.
    """

    _subband_data: Dict[int, S]

    def __init__(self: MonitorDataStore) -> None:
        """Initialise data store."""
        self._subband_data = {}

    def update_subband(self: MonitorDataStore, subband_id: int, subband_data: S) -> None:
        """Update the stored subband data for a given subband id.

        This just updates an internal dictionary. Subclasses should only
        override this method if there is a specific reason to handle
        a subband, as the `monitor_data` method should be the main place
        to handle aggregation.

        :param subband_id: the subband that is being updated.
        :param subband_data: the data for the current subband.
        """
        self._subband_data[subband_id] = subband_data

    def reset(self: MonitorDataStore) -> None:
        """Reset the monitoring data state."""
        self._subband_data.clear()

    @property
    def monitor_data(self: MonitorDataStore) -> T:
        """Return the current calculated monitoring data.

        Implementations of this should aggregate the monitoring data
        to be what is the current snapshot of data.

        :returns: current monitoring data.
        """
        raise NotImplementedError("MonitorDataStore is abstract")


class MonitorDataHandler(Generic[S, T]):
    """Generic monitor data handler for subband.

    This handler needs to be constructed with a :py:class:`MonitorDataStore`
    that takes subband monitoring data (type `S`) and can aggregate
    that data to return a combined monitoring data object (type `T`).

    Since monitoring happens in the background and asynchronously
    the updates to the data store is guarded by a threading lock.

    There should be no need to override any of these methods.
    """

    def __init__(
        self: MonitorDataHandler,
        data_store: MonitorDataStore[S, T],
        monitor_data_callback: Callable[[T], None],
    ):
        """Initialise data handler.

        :param data_store: the monitoring data store to handle subband monitoring data.
        :param monitor_data_callback: the callback to call once subband monitoring data
            has been merged with other subband data.
        """
        self._monitor_lock = threading.Lock()
        self._data_store = data_store
        self._monitor_data_callback = monitor_data_callback
        # get initial data
        self._monitor_data = data_store.monitor_data

    def handle_subband_data(self: MonitorDataHandler, subband_id: int, subband_data: S) -> None:
        """Handle subband monitoring data.

        This will call the data store's :py:meth:`MonitorDataStore.update_subband` within a write
        lock. After updating the data store it will call the monitoring callback with the latest
        monitoring data from the data store.
        """
        with self._monitor_lock:
            self._data_store.update_subband(subband_id=subband_id, subband_data=subband_data)
            self.update_monitor_data(notify=True)

    @property
    def monitor_data(self: MonitorDataHandler) -> T:
        """Get current monitor data."""
        return self._monitor_data

    def reset_monitor_data(self: MonitorDataHandler) -> None:
        """Reset the monitor data store."""
        with self._monitor_lock:
            self._data_store.reset()
            self.update_monitor_data(notify=True)

    def update_monitor_data(self: MonitorDataHandler, notify: bool) -> None:
        """Update monitoring data.

        This method is used internally as well as by DSP to recalculate
        monitoring data. To force callback `notify` must be set to `True`.

        :param notify: whether to notify callback that there has been an update.
        :type notify: bool
        """
        self._monitor_data = self._data_store.monitor_data

        if notify:
            self._monitor_data_callback(self._monitor_data)
