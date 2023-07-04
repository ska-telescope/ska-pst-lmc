# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.
"""Module provides an purely abstract view of a PST Device."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from ska_tango_base.control_model import CommunicationStatus, HealthState

from ska_pst_lmc.util import TelescopeFacilityEnum


class PstDeviceInterface:
    """
    A purely abstract class to be implemented by Tango device classes.

    This class is used to abstract away any Tango functionality that component managers need to callback to
    the Tango device and in turn allow passing of the Tango device itself to the component manager but is
    abstracted. This class itself can be extended for a particular device/component_manager combination where
    there is a need for more specific functionality but without the need of exposing a callback.

    By being an abstract class this can be mocked to be used in testing.
    """

    def handle_communication_state_change(
        self: PstDeviceInterface, communication_state: CommunicationStatus
    ) -> None:
        """Handle a change in device's communication state."""
        raise NotImplementedError("PstDeviceInteface is abstract")

    def handle_component_state_change(self: PstDeviceInterface, *args: Any, **kwargs: Any) -> None:
        """Handle a change in the component's state."""
        raise NotImplementedError("PstDeviceInteface is abstract")

    def handle_attribute_value_update(self: PstDeviceInterface, attribute_name: str, value: Any) -> None:
        """
        Handle update of a device attribute value.

        :param attribute_name: the name of the attribute to update.
        :type attribute_name: str
        :param value: the new value of the attribute to update to.
        :type value: Any
        """
        raise NotImplementedError("PstDeviceInteface is abstract")

    @property
    def beam_id(self: PstDeviceInterface) -> int:
        """Get the beam id for the current device."""
        raise NotImplementedError("PstDeviceInteface is abstract")

    @property
    def device_name(self: PstDeviceInterface) -> str:
        """Get the name of the device."""
        raise NotImplementedError("PstDeviceInteface is abstract")

    def handle_fault(self: PstDeviceInterface, fault_msg: str) -> None:
        """Handle device going into a fault state."""
        raise NotImplementedError("PstDeviceInteface is abstract")

    @property
    def facility(self: PstDeviceInterface) -> TelescopeFacilityEnum:
        """Get the facility that this device is being used for."""
        raise NotImplementedError("PstDeviceInteface is abstract")

    def update_health_state(self: PstDeviceInterface, health_state: HealthState) -> None:
        """
        Update the health state of device.

        :param health_state: the new health state of the Tango device.
        :type health_state: HealthState
        """
        raise NotImplementedError("PstDeviceInteface is abstract")


T = TypeVar("T")


class PstApiDeviceInterface(PstDeviceInterface, Generic[T]):
    """A generic `PstDeviceInterface` used by API based device components.

    This interface is used by devices like SMRB.MGMT, RECV.MGMT, etc that
    wrap APIs to processes like SMRB.CORE. These devices all get and process
    monitoring data from the remote system.

    This is a generic class over the class of the data model for the API monitoring.
    This avoids unnecessary casts within the Tango device implementation.
    """

    @property
    def process_api_endpoint(self: PstApiDeviceInterface) -> str:
        """Get the process API endpoint."""
        raise NotImplementedError("PstApiDeviceInterface is abstract")

    @property
    def monitoring_polling_rate(self: PstApiDeviceInterface) -> int:
        """Get the monitoring polling rate."""
        raise NotImplementedError("PstApiDeviceInterface is abstract")

    def handle_monitor_data_update(self: PstApiDeviceInterface, monitor_data: T) -> None:
        """
        Handle monitoring data.

        This is a generic extension of `PstDeviceInteface` to allow for handling
        of monitoring data. This is designed so that there is no need to send
        through a monitoring callback to the component manager.
        """
        raise NotImplementedError("PstApiDeviceInterface is abstract")
