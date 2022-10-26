# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides an implementation of the BEAM PST component manager."""

from __future__ import annotations

import json
import logging
from threading import Event
from typing import Any, Callable, List, Optional, Tuple

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import AdminMode, CommunicationStatus, PowerState
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component.component_manager import PstComponentManager
from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.util.long_running_command_interface import LongRunningCommandInterface

TaskResponse = Tuple[TaskStatus, str]
RemoteTaskResponse = Tuple[List[TaskStatus], List[str]]

__all__ = [
    "PstBeamComponentManager",
]

ActionResponse = Tuple[List[str], List[str]]
RemoteDeviceAction = Callable[[PstDeviceProxy], ActionResponse]
CompletionCallback = Callable[[Callable, List[str]], None]


class _RemoteJob:
    def __init__(
        self: _RemoteJob,
        action: RemoteDeviceAction,
        long_running_client: LongRunningCommandInterface,
        completion_callback: CompletionCallback,
        logger: logging.Logger,
    ):
        self._action = action
        self._long_running_client = long_running_client
        self._completion_callback = completion_callback
        self._logger = logger

    def __call__(
        self: _RemoteJob,
        *args: Any,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs: Any,
    ) -> None:
        def _completion_callback(command_ids: List[str]) -> None:
            self._completion_callback(task_callback, command_ids)  # type: ignore

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            self._long_running_client.execute_long_running_command(
                self._action,
                on_completion_callback=_completion_callback,
            )
        except Exception as e:
            self._logger.warning("Error in submitting long running commands to remote devices", exc_info=True)
            if task_callback:
                task_callback(status=TaskStatus.FAILED, result=str(e), exception=e)


class PstBeamComponentManager(PstComponentManager):
    """Component manager for the BEAM component in PST.LMC.

    Since the BEAM component is a logical device, this component
    manager is used to orchestrate the process devices, such as
    BEAM, RECV.

    Commands that are executed on this component manager are
    sent to instances of :py:class:`PstDeviceProxy` for each
    device that the BEAM device manages.

    This component manager only takes the fully-qualified device
    name (FQDN) for the remote devices, but uses the
    :py:class:`DeviceProxyFactory` to retrieve instances of the
    device proxies that commands should be sent to.
    """

    _smrb_device: PstDeviceProxy
    _recv_device: PstDeviceProxy
    _dsp_device: PstDeviceProxy

    def __init__(
        self: PstBeamComponentManager,
        device_name: str,
        smrb_fqdn: str,
        recv_fqdn: str,
        dsp_fqdn: str,
        logger: logging.Logger,
        communication_state_callback: Callable[[CommunicationStatus], None],
        component_state_callback: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialise component manager.

        :param smrb_fqdn: the fully qualified device name (FQDN) of the
            shared memory ring buffer (SMRB) TANGO device.
        :param recv_fqdn: the FQDN of the Receive TANGO device.
        :param dsp_fqdn: the FQDN of the Digital Signal processing (DSP) TANGO device.
        :param simulation_mode: enum to track if component should be
            in simulation mode or not.
        :param logger: a logger for this object to use
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_fault_callback: callback to be called when the
            component faults (or stops faulting)
        """
        self._smrb_device = DeviceProxyFactory.get_device(smrb_fqdn)
        self._recv_device = DeviceProxyFactory.get_device(recv_fqdn)
        self._dsp_device = DeviceProxyFactory.get_device(dsp_fqdn)
        self._remote_devices = [self._smrb_device, self._recv_device, self._dsp_device]
        self._subscribed = False
        self._long_running_client = LongRunningCommandInterface(
            tango_devices=self._remote_devices,
            logger=logger,
        )
        super().__init__(
            device_name,
            logger,
            communication_state_callback,
            component_state_callback,
            *args,
            power=PowerState.UNKNOWN,
            fault=None,
            **kwargs,
        )

    def _handle_communication_state_change(
        self: PstBeamComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if communication_state == CommunicationStatus.NOT_ESTABLISHED:
            # fake going through states to have the communication established.
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._component_state_callback(fault=None, power=PowerState.OFF)
        elif communication_state == CommunicationStatus.DISABLED:
            self._component_state_callback(fault=None, power=PowerState.UNKNOWN)
            self._update_communication_state(CommunicationStatus.DISABLED)

    def update_admin_mode(self: PstBeamComponentManager, admin_mode: AdminMode) -> None:
        """Update the admin mode of the remote devices.

        The adminMode of the remote devices should only be managed through the BEAM
        device, and this method is called from the :py:class:`PstBeam` device to
        make sure that the component manager will update the remote devices.
        """
        self._smrb_device.adminMode = admin_mode
        self._recv_device.adminMode = admin_mode
        self._dsp_device.adminMode = admin_mode

    def _submit_remote_job(
        self: PstBeamComponentManager,
        action: RemoteDeviceAction,
        task_callback: Callable,
        completion_callback: CompletionCallback,
    ) -> TaskResponse:
        remote_job = _RemoteJob(
            action, self._long_running_client, completion_callback=completion_callback, logger=self.logger
        )

        return self.submit_task(
            remote_job,
            task_callback=task_callback,
        )

    @check_communicating
    def on(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the On commands {command_ids} have completed.")
            self._component_state_callback(power=PowerState.ON)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.On(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def off(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'Off' commands {command_ids} have completed.")
            self._component_state_callback(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.Off(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def standby(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Put the component is standby.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'Standy' commands {command_ids} have completed.")
            self._component_state_callback(power=PowerState.STANDBY)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.Standby(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def reset(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """
        Reset the component.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'Reset' commands {command_ids} have completed.")
            self._component_state_callback(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.Reset(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def assign(self: PstBeamComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Assign resources to the component.

        :param resources: resources to be assigned
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'AssignResources' commands {command_ids} have completed.")
            self._component_state_callback(resourced=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        resources_str = json.dumps(resources)

        return self._submit_remote_job(
            action=lambda d: d.AssignResources(resources_str),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def release(self: PstBeamComponentManager, resources: dict, task_callback: Callable) -> TaskResponse:
        """
        Release resources from the component.

        :param resources: resources to be released
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'ReleaseResources' commands {command_ids} have completed.")
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        resources_str = json.dumps(resources)

        return self._submit_remote_job(
            action=lambda d: d.ReleaseResources(resources_str),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def release_all(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Release all resources."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'ReleaseAllResources' commands {command_ids} have completed.")
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.ReleaseAllResources(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def configure_scan(
        self: PstBeamComponentManager, configuration: dict, task_callback: Callable
    ) -> TaskResponse:
        """
        Configure scan for the component.

        :param configuration: the scan configuration.
        :type configuration: dict
        """

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'Configure' commands {command_ids} have completed.")
            self._component_state_callback(configured=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        configuration_str = json.dumps(configuration)

        return self._submit_remote_job(
            action=lambda d: d.Configure(configuration_str),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def deconfigure_scan(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure scan for this component."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'End' commands {command_ids} have completed.")
            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.End(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def start_scan(self: PstBeamComponentManager, args: dict, task_callback: Callable) -> TaskResponse:
        """Start scanning."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'Scan' commands {command_ids} have completed.")
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        args_str = json.dumps(args)

        return self._submit_remote_job(
            action=lambda d: d.Scan(args_str),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def stop_scan(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Stop scanning."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'EndScan' commands {command_ids} have completed.")
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.EndScan(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def abort(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""
        # raise NotImplementedError("SubarrayComponentManager is abstract.")
        self._smrb_device.Abort()
        self._recv_device.Abort()
        self._dsp_device.Abort()
        return super().abort_tasks(task_callback)

    def obsreset(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Reset the component to unconfigured but do not release resources."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'ObsReset' commands {command_ids} have completed.")
            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.ObsReset(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def restart(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Deconfigure and release all resources."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'Restart' commands {command_ids} have completed.")
            self._component_state_callback(configured=False, resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.Restart(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def go_to_fault(self: PstBeamComponentManager, task_callback: Callable) -> TaskResponse:
        """Put all the sub-devices into a FAULT state."""

        def _completion_callback(task_callback: Callable, command_ids: List[str]) -> None:
            self.logger.debug(f"All the 'GoToFault' commands {command_ids} have completed.")
            self._component_state_callback(obsfault=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            action=lambda d: d.GoToFault(),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )
