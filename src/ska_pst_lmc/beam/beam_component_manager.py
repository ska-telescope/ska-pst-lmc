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
from typing import Any, Callable, Dict, List, Optional, Tuple

from ska_tango_base.base import check_communicating
from ska_tango_base.control_model import AdminMode, CommunicationStatus, PowerState
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.component.component_manager import PstComponentManager
from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.util import DeviceCommandJob, Job, SequentialJob, submit_job
from ska_pst_lmc.util.callback import Callback

TaskResponse = Tuple[TaskStatus, str]
RemoteTaskResponse = Tuple[List[TaskStatus], List[str]]

__all__ = [
    "PstBeamComponentManager",
]

ActionResponse = Tuple[List[str], List[str]]
RemoteDeviceAction = Callable[[PstDeviceProxy], ActionResponse]


class _RemoteJob:
    def __init__(
        self: _RemoteJob,
        job: Job,
        completion_callback: Callback,
        logger: logging.Logger,
    ):
        self._job = job
        self._completion_callback = completion_callback
        self._logger = logger

    def __call__(
        self: _RemoteJob,
        *args: Any,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
        **kwargs: Any,
    ) -> None:
        def _completion_callback() -> None:
            self._completion_callback(task_callback)  # type: ignore

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            submit_job(job=self._job, callback=_completion_callback)
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
            self._push_component_state_update(fault=None, power=PowerState.OFF)
        elif communication_state == CommunicationStatus.DISABLED:
            self._push_component_state_update(fault=None, power=PowerState.UNKNOWN)
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
        job: Job,
        task_callback: Callback,
        completion_callback: Callback,
    ) -> TaskResponse:
        remote_job = _RemoteJob(job, completion_callback=completion_callback, logger=self.logger)

        return self.submit_task(
            remote_job,
            task_callback=task_callback,
        )

    @check_communicating
    def on(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component on.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'on' commands have completed.")
            self._push_component_state_update(power=PowerState.ON)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(devices=self._remote_devices, action=lambda d: d.On()),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def off(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Turn the component off.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Off' commands have completed.")
            self._push_component_state_update(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.Off(),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def standby(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Put the component is standby.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Standy' commands have completed.")
            self._push_component_state_update(power=PowerState.STANDBY)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.Standby(),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    @check_communicating
    def reset(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """
        Reset the component.

        :param task_callback: callback to be called when the status of
            the command changes
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Reset' commands have completed.")
            self._push_component_state_update(power=PowerState.OFF)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.Reset(),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def configure_scan(
        self: PstBeamComponentManager, configuration: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """
        Configure scan for the component.

        :param configuration: the scan configuration.
        :type configuration: Dict[str, Any]
        """

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'ConfigureScan' commands have completed.")
            self._push_component_state_update(configured=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        configuration_str = json.dumps(configuration)

        return self._submit_remote_job(
            job=SequentialJob(
                tasks=[
                    # first do configre_beam on SMRB
                    DeviceCommandJob(
                        devices=[self._smrb_device],
                        action=lambda d: d.ConfigureBeam(configuration_str),
                    ),
                    # now do configure_beam on DSP and RECV, this can be done in parallel
                    DeviceCommandJob(
                        devices=[self._dsp_device, self._recv_device],
                        action=lambda d: d.ConfigureBeam(configuration_str),
                    ),
                    # now configure scan on SMRB and RECV (smrb is no-op) in parallel
                    DeviceCommandJob(
                        devices=[self._smrb_device, self._recv_device],
                        action=lambda d: d.ConfigureScan(configuration_str),
                    ),
                    # now configure scan on the DSP device.
                    DeviceCommandJob(
                        devices=[self._dsp_device],
                        action=lambda d: d.ConfigureScan(configuration_str),
                    ),
                ]
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def deconfigure_scan(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Deconfigure scan for this component."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'GoToIdle' commands have completed.")
            self._push_component_state_update(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=SequentialJob(
                tasks=[
                    # need to deconfigure scan of all processes, this can be done in parallel.
                    DeviceCommandJob(
                        devices=self._remote_devices,
                        action=lambda d: d.DeconfigureScan(),
                    ),
                    # need to release the ring buffer clients before deconfiguring SMRB
                    DeviceCommandJob(
                        devices=[self._dsp_device, self._recv_device],
                        action=lambda d: d.DeconfigureBeam(),
                    ),
                    DeviceCommandJob(
                        devices=[self._smrb_device],
                        action=lambda d: d.DeconfigureBeam(),
                    ),
                ],
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def start_scan(
        self: PstBeamComponentManager, args: Dict[str, Any], task_callback: Callback = None
    ) -> TaskResponse:
        """Start scanning."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'Scan' commands have completed.")
            self._push_component_state_update(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        scan_id = int(args["scan_id"])

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.Scan(scan_id),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def stop_scan(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Stop scanning."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'EndScan' commands have completed.")
            self._push_component_state_update(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.EndScan(),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def abort(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Tell the component to abort whatever it was doing."""
        # raise NotImplementedError("SubarrayComponentManager is abstract.")
        self._smrb_device.Abort()
        self._recv_device.Abort()
        self._dsp_device.Abort()
        return super().abort_tasks(task_callback)

    def obsreset(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Reset the component to unconfigured but do not release resources."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'ObsReset' commands have completed.")
            self._push_component_state_update(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.ObsReset(),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )

    def go_to_fault(self: PstBeamComponentManager, task_callback: Callback = None) -> TaskResponse:
        """Put all the sub-devices into a FAULT state."""

        def _completion_callback(task_callback: Callable) -> None:
            self.logger.debug("All the 'GoToFault' commands have completed.")
            self._push_component_state_update(obsfault=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")

        return self._submit_remote_job(
            job=DeviceCommandJob(
                devices=self._remote_devices,
                action=lambda d: d.GoToFault(),
            ),
            task_callback=task_callback,
            completion_callback=_completion_callback,
        )
