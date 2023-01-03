# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides the base Component Manager fror PST.LMC."""

from __future__ import annotations

import functools
import logging
from threading import Event
from typing import Any, Callable, Dict, Generic, Optional, Tuple, TypeVar, cast

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import CommunicationStatus, HealthState, PowerState, SimulationMode
from ska_tango_base.csp.obs import CspObsComponentManager
from ska_tango_base.executor import TaskExecutorComponentManager, TaskStatus

from ska_pst_lmc.component.process_api import PstProcessApi
from ska_pst_lmc.component.pst_device_interface import PstApiDeviceInterface, PstDeviceInterface
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.callback import Callback, callback_safely, wrap_callback

__all__ = [
    "PstApiComponentManager",
    "PstComponentManager",
    "TaskResponse",
]


TaskResponse = Tuple[TaskStatus, str]

DeviceInterface = TypeVar("DeviceInterface", bound=PstDeviceInterface)


class PstComponentManager(Generic[DeviceInterface], TaskExecutorComponentManager, CspObsComponentManager):
    """
    Base Component Manager for the PST.LMC. subsystem.

    This base class is used to provide the common functionality of the
    PST Tango components, such as providing the the communication with
    processes that are running (i.e. RECV, DSP, or SMRB).

    This class also helps abstract away calling out to whether we're
    using a simulated process or a real subprocess.

    This component manager extects from the :py:class:`CspObsComponentManager`.
    For more details about this check the
    `CSP obs component manager
    <https://developer.skao.int/projects/ska-tango-base/en/latest/api/csp/obs/component_manager.html>`_
    docs.
    """

    _simuation_mode: SimulationMode

    def __init__(
        self: PstComponentManager,
        *,
        device_interface: DeviceInterface,
        logger: logging.Logger,
        simulation_mode: SimulationMode = SimulationMode.TRUE,
        **kwargs: Any,
    ) -> None:
        """Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This
            is used within the gRPC process to identify who is
            doing the calling.
        :type device_name: str
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :type simulation_mode: `SimulationMode`
        :param logger: a logger for this object to use
        :type logger: `logging.Logger`
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :type communication_status_changed_callback: `Callable`
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        :type component_fault_callback: `Callable`
        :param beam_id: the ID of the beam that this component manger is for.
            The default value is 1 (used for testing).
        :type beam_id: int
        """
        self._device_interface = device_interface
        self._property_callback = device_interface.handle_attribute_value_update
        self._simuation_mode = simulation_mode
        self._background_task_processor = BackgroundTaskProcessor(default_logger=logger)
        self._scan_id = 0
        self._config_id = ""
        super().__init__(
            logger=logger,
            communication_state_callback=device_interface.handle_communication_state_change,
            component_state_callback=device_interface.handle_component_state_change,
            **kwargs,
        )

    @property
    def beam_id(self: PstComponentManager) -> int:
        """Return the beam id for the current component.

        This value is set during the construction of the component manager,
        and is injected from the `DeviceID` property of the TANGO device.
        """
        return self._device_interface.beam_id

    @property
    def device_name(self: PstComponentManager) -> str:
        """Get the name of the current device."""
        return self._device_interface.device_name

    def start_communicating(self: PstComponentManager) -> None:
        """
        Establish communication with the component, then start monitoring.

        This is the place to do things like:

        * Initiate a connection to the component (if your communication
          is connection-oriented)
        * Subscribe to component events (if using "pull" model)
        * Start a polling loop to monitor the component (if using a
          "push" model)
        """
        if self._communication_state == CommunicationStatus.ESTABLISHED:
            return
        if self._communication_state == CommunicationStatus.DISABLED:
            self._handle_communication_state_change(CommunicationStatus.NOT_ESTABLISHED)

    def stop_communicating(self: PstComponentManager) -> None:
        """
        Cease monitoring the component, and break off all communication with it.

        For example,

        * If you are communicating over a connection, disconnect.
        * If you have subscribed to events, unsubscribe.
        * If you are running a polling loop, stop it.
        """
        if self._communication_state == CommunicationStatus.DISABLED:
            return

        self._handle_communication_state_change(CommunicationStatus.DISABLED)

    def _handle_communication_state_change(
        self: PstComponentManager, communication_state: CommunicationStatus
    ) -> None:
        raise NotImplementedError("PstComponentManager is abstract.")

    @property
    def simulation_mode(self: PstComponentManager) -> SimulationMode:
        """Get value of simulation mode state.

        :returns: current simulation mode state.
        """
        return self._simuation_mode

    @simulation_mode.setter
    def simulation_mode(self: PstComponentManager, simulation_mode: SimulationMode) -> None:
        """Set simulation mode state.

        :param simulation_mode: the new simulation mode value.
        :type simulation_mode: :py:class:`SimulationMode`
        """
        if self._simuation_mode != simulation_mode:
            self._simuation_mode = simulation_mode
            self._simulation_mode_changed()

    def _simulation_mode_changed(self: PstComponentManager) -> None:
        """Handle change of simulation mode.

        Default implementation of this is to do nothing. It is up to the individual devices
        to handle what it means when the simulation mode changes.
        """

    @property
    def config_id(self: PstComponentManager) -> str:
        """Return the configuration id."""
        return self._config_id

    @config_id.setter
    def config_id(self: PstComponentManager, config_id: str) -> None:
        """Set the configuration id."""
        self._config_id = config_id

    @property
    def scan_id(self: PstComponentManager) -> int:
        """Return the scan id."""
        return self._scan_id

    @scan_id.setter
    def scan_id(self: PstComponentManager, scan_id: int) -> None:
        """Set the scan id."""
        self._scan_id = scan_id

    # ---------------
    # Commands
    # ---------------

    @check_communicating
    def off(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Callback = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)
            self._push_component_state_update(power=PowerState.OFF)
            cast(PstDeviceInterface, self._device_interface).update_health_state(
                health_state=HealthState.UNKNOWN
            )
            callback_safely(task_callback, status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    @check_communicating
    def standby(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Put the component into low-power standby mode.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Callback = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)
            self._push_component_state_update(power=PowerState.STANDBY)
            callback_safely(task_callback, status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    @check_communicating
    def on(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Callback = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)
            self._push_component_state_update(power=PowerState.ON)
            cast(PstDeviceInterface, self._device_interface).update_health_state(health_state=HealthState.OK)
            callback_safely(task_callback, status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    @check_communicating
    def reset(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Reset the component (from fault state).

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _task(
            *args: Any,
            task_callback: Callback = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)
            self._push_component_state_update(fault=False, power=PowerState.OFF)
            callback_safely(task_callback, status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    def configure_beam(
        self: PstComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure the beam specific configuration of the component.

        :param configuration: configuration for beam
        :type configuration: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    def deconfigure_beam(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure the component's beam configuration.

        This will release all the resources associated with the component, including the SMRBs.

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    def configure_scan(
        self: PstComponentManager, configuration: Dict[str, Any], task_callback: Callback
    ) -> TaskResponse:
        """
        Configure the component for a scan.

        :param configuration: the configuration to be configured
        :type configuration: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    def deconfigure(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure this component for current scan configuration.

        .. deprecated:: 0.2.2
            Use :meth:`deconfigure_scan`

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        return self.deconfigure_scan(task_callback=task_callback)

    def deconfigure_scan(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure this component for current scan configuration.

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    def scan(self: PstComponentManager, scan_id: int, task_callback: Callback = None) -> TaskResponse:
        """Start scanning.

        .. deprecated:: 0.2.2
            Use :meth:`start_scan`

        :param scan_id: the ID for the scan that is to be performed.
        :type scan_id: int
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callable
        """
        args: Dict[str, Any] = {"scan_id": scan_id}
        return self.start_scan(args=args, task_callback=task_callback)

    def start_scan(
        self: PstComponentManager, args: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Start scanning.

        :param args: scan arguments (i.e start time)
        :type args: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    def end_scan(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning.

        .. deprecated:: 0.2.2
            Use :meth:`stop_scan`

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        return self.stop_scan(task_callback=task_callback)

    def stop_scan(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning.

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        raise NotImplementedError("PstComponentManager is abstract.")

    def obsreset(self: PstComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Reset the component to unconfigured but do not release resources."""

        def _task(
            *args: Any,
            task_callback: Callback = None,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            callback_safely(task_callback, status=TaskStatus.IN_PROGRESS)
            self._push_component_state_update(configured=False)
            callback_safely(task_callback, status=TaskStatus.COMPLETED, result="Completed")

        return self.submit_task(_task, task_callback=task_callback)

    def go_to_fault(
        self: PstComponentManager, fault_msg: str, task_callback: Callback = None
    ) -> TaskResponse:
        """Set the component into a FAULT state.

        For BEAM this will make the sub-devices be put into a FAULT state. For
        API backed component managers it is expected that the service backing that
        API should be put into a FAULT state.
        """
        raise NotImplementedError("PstComponentManager is abstract class")


T = TypeVar("T")
Api = TypeVar("Api", bound=PstProcessApi)


class PstApiComponentManager(Generic[T, Api], PstComponentManager[PstApiDeviceInterface[T]]):
    """
    A base component Manager for the PST.LMC. that uses an API.

    Instances of this component manager are required to provide an
    instance of a :py:class:`PstProcessApi` to delegate functionality
    to. If the simulation mode changes then the instances are expected
    to handle changing between a simulation API and a real implementation
    of the API; the interface for the simulation and real API are to be
    the same.

    Only components that use an external process, such as RECV and SMRB
    are to be extended from this class. Components such as BEAM need
    to use :py:class:`PstComponentManager` as they don't use a process
    API.
    """

    def __init__(
        self: PstApiComponentManager,
        *,
        device_interface: PstApiDeviceInterface[T],
        api: Api,
        logger: logging.Logger,
        **kwargs: Any,
    ) -> None:
        """Initialise instance of the component manager.

        :param device_name: the FQDN of the current device. This
            is used within the gRPC process to identify who is
            doing the calling.
        :type device_name: str
        :param api: an API object used to delegate functionality to.
        :type api: `PstProcessApi`
        :param logger: a logger for this object to use
        :type logger: `logging.Logger`
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :type communication_status_changed_callback: `Callable`
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        :type component_fault_callback: `Callable`
        """
        self._api = api
        self._monitor_polling_rate = device_interface.monitor_polling_rate
        super().__init__(device_interface=device_interface, logger=logger, **kwargs)

    def _handle_communication_state_change(
        self: PstApiComponentManager, communication_state: CommunicationStatus
    ) -> None:
        """Handle change in communication state."""
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            self._connect_to_api()
        elif communication_state == CommunicationStatus.DISABLED:
            self._disconnect_from_api()

    def _connect_to_api(self: PstApiComponentManager) -> None:
        """Establish connection to API component."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._api.connect()
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._push_component_state_update(fault=None, power=PowerState.OFF)

    def _disconnect_from_api(self: PstApiComponentManager) -> None:
        """Establish connection to API component."""
        self._api.disconnect()
        self._update_communication_state(CommunicationStatus.DISABLED)
        self._push_component_state_update(fault=None, power=PowerState.UNKNOWN)

    def _simulation_mode_changed(self: PstApiComponentManager) -> None:
        """Handle change of simulation mode."""
        curr_communication_state = self.communication_state
        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.debug(
                f"{self.device_name} simulation mode changed while "
                + "communicating so stopping communication."
            )
            self.stop_communicating()

        self._update_api()

        if curr_communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.debug(
                f"{self.device_name} simulation mode changed while "
                + "communicating so restarting communication."
            )
            self.start_communicating()

    def _update_api(self: PstApiComponentManager) -> None:
        """Update API used by component manager.

        This is called when there is a change in the simulation mode.
        """
        raise NotImplementedError("PstApiComponentManager is abstract.")

    @property
    def api_endpoint(self: PstApiComponentManager) -> str:
        """Get the API endpoint."""
        return cast(PstApiDeviceInterface, self._device_interface).process_api_endpoint

    def configure_beam(
        self: PstApiComponentManager, resources: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure the beam resources of the component.

        :param resources: resources to be assigned
        :type resources: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        return self._submit_background_task(
            functools.partial(self._api.configure_beam, resources=resources), task_callback=task_callback
        )

    def deconfigure_beam(self: PstApiComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure the component's beam configuration.

        This will release all the resources associated with the component, including the SMRBs.

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        return self._submit_background_task(self._api.deconfigure_beam, task_callback=task_callback)

    def configure_scan(
        self: PstApiComponentManager, configuration: Dict[str, Any], task_callback: Callback
    ) -> TaskResponse:
        """
        Configure the component for a scan.

        :param configuration: the configuration to be configured
        :type configuration: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        return self._submit_background_task(
            functools.partial(self._api.configure_scan, configuration=configuration),
            task_callback=task_callback,
        )

    def deconfigure_scan(self: PstApiComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure this component for current scan configuration.

        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        return self._submit_background_task(self._api.deconfigure_scan, task_callback=task_callback)

    def start_scan(
        self: PstApiComponentManager, args: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Start scanning.

        :param args: scan arguments (i.e start time)
        :type args: Dict[str, Any]
        :param task_callback: callback for background processing to update device status.
        :type task_callback: Callback
        """
        # should be for how long the scan is and update based on that.
        return self._submit_background_task(
            functools.partial(self._api.start_scan, args), task_callback=task_callback
        )

    def stop_scan(self: PstApiComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning."""
        return self._submit_background_task(self._api.stop_scan, task_callback=task_callback)

    def abort(self: PstApiComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Abort current process.

        The only long lived process for API based devices is that of SCANNING. However,
        if another system fails this can be used to put all the subsystems into an ABORTED
        state.
        """
        self._api.abort(task_callback=wrap_callback(task_callback))
        return TaskStatus.IN_PROGRESS, "Aborting"

    def obsreset(self: PstApiComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Reset service.

        This is used to reset a service in ABORTED or FAULT states back to an IDLE state.
        This will deconfigure a scan if already configured but will keep the assigned
        resources.
        """

        def _task_callback(*args: Any, **kwargs: Any) -> None:
            status: Optional[TaskStatus] = kwargs.get("status", None)
            if status == TaskStatus.COMPLETED:
                self._device_interface.update_health_state(health_state=HealthState.OK)

            callback_safely(task_callback, *args, **kwargs)

        return self._submit_background_task(self._api.reset, task_callback=_task_callback)

    def go_to_fault(
        self: PstApiComponentManager, fault_msg: str, task_callback: Callback = None
    ) -> TaskResponse:
        """Put the service into a FAULT state."""

        def _task(
            *args: Any, task_callback: Callback, task_abort_event: Optional[Event] = None, **kwargs: Any
        ) -> None:
            # allow wrapping of callback to avoid needint to check if None or not.
            wrapped_callback = wrap_callback(task_callback)
            wrapped_callback(status=TaskStatus.IN_PROGRESS)
            self._api.go_to_fault()
            self._device_interface.handle_fault(fault_msg=fault_msg)
            wrapped_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_background_task(_task, task_callback=task_callback)

    def _submit_background_task(
        self: PstApiComponentManager, task: Callable, task_callback: Callback
    ) -> TaskResponse:
        def _task(
            *args: Any,
            task_callback: Callback,
            task_abort_event: Optional[Event] = None,
            **kwargs: Any,
        ) -> None:
            task(task_callback=task_callback)

        return self.submit_task(_task, task_callback=task_callback)
