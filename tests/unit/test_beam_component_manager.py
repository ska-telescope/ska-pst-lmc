# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the BEAM component managers class."""

import json
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.control_model import AdminMode, CommunicationStatus, PowerState
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.beam.beam_component_manager import PstBeamComponentManager
from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor


@pytest.fixture
def logger() -> logging.Logger:
    """Create logger fixture."""
    return logging.getLogger("test")


@pytest.fixture
def smrb_fqdn() -> str:
    """Create SMRB FQDN fixture."""
    return "test/smrb/1"


@pytest.fixture
def smrb_device_proxy(smrb_fqdn: str) -> PstDeviceProxy:
    """Create SMRB Device Proxy fixture."""
    proxy = MagicMock()
    proxy.fqdn = smrb_fqdn
    return proxy


@pytest.fixture
def recv_fqdn() -> str:
    """Create RECV FQDN fixture."""
    return "test/recv/1"


@pytest.fixture
def recv_device_proxy(recv_fqdn: str) -> PstDeviceProxy:
    """Create RECV device proxy fixture."""
    proxy = MagicMock()
    proxy.fqdn = recv_fqdn
    return proxy


@pytest.fixture
def dsp_fqdn() -> str:
    """Create DSP FQDN fixture."""
    return "test/dsp/1"


@pytest.fixture
def dsp_device_proxy(dsp_fqdn: str) -> PstDeviceProxy:
    """Create RECV device proxy fixture."""
    proxy = MagicMock()
    proxy.fqdn = dsp_fqdn
    return proxy


@pytest.fixture
def background_task_processor() -> BackgroundTaskProcessor:
    """Create Background Processor fixture."""
    return MagicMock()


@pytest.fixture
def communication_state_callback() -> Callable[[CommunicationStatus], None]:
    """Create communication state callback fixture."""
    return MagicMock()


@pytest.fixture
def component_state_callback() -> Callable:
    """Create component state callback fixture."""
    return MagicMock()


@pytest.fixture
def component_manager(
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
    logger: logging.Logger,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    background_task_processor: BackgroundTaskProcessor,
    monkeypatch: pytest.MonkeyPatch,
) -> PstBeamComponentManager:
    """Create PST Beam Component fixture."""
    smrb_fqdn = smrb_device_proxy.fqdn
    recv_fqdn = recv_device_proxy.fqdn
    dsp_fqdn = dsp_device_proxy.fqdn

    def _get_device(fqdn: str) -> PstDeviceProxy:
        if fqdn == smrb_fqdn:
            return smrb_device_proxy
        elif fqdn == recv_fqdn:
            return recv_device_proxy
        else:
            return dsp_device_proxy

    monkeypatch.setattr(DeviceProxyFactory, "get_device", _get_device)

    return PstBeamComponentManager(
        "test/beam/1",
        smrb_fqdn,
        recv_fqdn,
        dsp_fqdn,
        logger,
        communication_state_callback,
        component_state_callback,
        background_task_processor=background_task_processor,
    )


@pytest.mark.parametrize(
    "curr_communication_status, new_communication_status, expected_update_states, expected_power_state",
    [
        (
            CommunicationStatus.DISABLED,
            CommunicationStatus.NOT_ESTABLISHED,
            [CommunicationStatus.NOT_ESTABLISHED, CommunicationStatus.ESTABLISHED],
            PowerState.OFF,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            [CommunicationStatus.DISABLED],
            PowerState.UNKNOWN,
        ),
        (CommunicationStatus.ESTABLISHED, CommunicationStatus.ESTABLISHED, [], None),
    ],
)
def test_component_manager_handle_communication_state_change(
    component_manager: PstBeamComponentManager,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    curr_communication_status: CommunicationStatus,
    new_communication_status: CommunicationStatus,
    expected_update_states: List[CommunicationStatus],
    expected_power_state: Optional[PowerState],
) -> None:
    """Test component manager handles communication state changes corrrectly."""
    component_manager._communication_state = curr_communication_status

    component_manager._handle_communication_state_change(new_communication_status)

    if len(expected_update_states) == 0:
        communication_state_callback.assert_not_called()  # type: ignore
    else:
        calls = [call(s) for s in expected_update_states]
        communication_state_callback.assert_has_calls(calls)  # type: ignore
        assert component_manager._communication_state == expected_update_states[-1]

    if expected_power_state is not None:
        component_state_callback.assert_called_once_with(  # type: ignore
            fault=None, power=expected_power_state
        )
    else:
        component_state_callback.assert_not_called()  # type: ignore


def test_component_manager_delegates_admin_mode(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
) -> None:
    """Test component manager delegates setting admin mode to sub-component devices."""
    for a in list(AdminMode):
        component_manager.update_admin_mode(a)

        assert smrb_device_proxy.adminMode == a
        assert recv_device_proxy.adminMode == a
        assert dsp_device_proxy.adminMode == a


def test_component_manager_calls_abort_on_subdevices(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
) -> None:
    """Test component manager delegates setting admin mode to sub-component devices."""
    task_executor = MagicMock()
    task_executor.abort.return_value = (TaskStatus.IN_PROGRESS, "Aborting tasks")

    component_manager._task_executor = task_executor
    callback = MagicMock()
    (status, message) = component_manager.abort(task_callback=callback)

    assert status == TaskStatus.IN_PROGRESS
    assert message == "Aborting tasks"

    smrb_device_proxy.Abort.assert_called_once()
    recv_device_proxy.Abort.assert_called_once()
    dsp_device_proxy.Abort.assert_called_once()

    task_executor.abort.assert_called_once()


@pytest.fixture
def request_params(
    method_name: str,
    configure_beam_request: Dict[str, Any],
    configure_scan_request: Dict[str, Any],
    scan_request: dict,
) -> Optional[Any]:
    """Get request parameters for a given method name."""
    if method_name == "assign":
        return configure_beam_request
    elif method_name == "configure":
        return configure_scan_request
    elif method_name == "release":
        return {}
    elif method_name == "scan":
        return json.dumps(scan_request)
    else:
        return None


@pytest.mark.parametrize(
    "method_name, remote_action_supplier, component_state_callback_params",
    [
        ("on", lambda d: d.On, {"power": PowerState.ON}),
        ("off", lambda d: d.Off, {"power": PowerState.OFF}),
        ("reset", lambda d: d.Reset, {"power": PowerState.OFF}),
        ("standby", lambda d: d.Standby, {"power": PowerState.STANDBY}),
        ("assign", lambda d: d.AssignResources, {"resourced": True}),
        ("release", lambda d: d.ReleaseResources, {"resourced": False}),
        ("release_all", lambda d: d.ReleaseAllResources, {"resourced": False}),
        ("configure", lambda d: d.Configure, {"configured": True}),
        ("deconfigure", lambda d: d.End, {"configured": False}),
        ("scan", lambda d: d.Scan, {"scanning": True}),
        ("end_scan", lambda d: d.EndScan, {"scanning": False}),
        ("obsreset", lambda d: d.ObsReset, {"configured": False}),
        ("restart", lambda d: d.Restart, {"configured": False, "resourced": False}),
        ("go_to_fault", lambda d: d.GoToFault, {"obsfault": True}),
    ],
)
def test_remote_actions(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
    component_state_callback: Callable,
    method_name: str,
    request_params: Optional[Any],
    remote_action_supplier: Callable[[PstDeviceProxy], Callable],
    component_state_callback_params: Optional[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert that actions that need to be delegated to remote devices."""
    task_callback = MagicMock()

    def _submit_task(
        func: Callable,
        args: Optional[Any] = None,
        kwargs: Optional[dict] = None,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        args = args or []
        kwargs = kwargs or {}
        func(*args, task_callback=task_callback, task_abort_event=threading.Event(), **kwargs)
        if task_callback is not None:
            task_callback(status=TaskStatus.QUEUED)
        return TaskStatus.QUEUED, "Task queued"

    monkeypatch.setattr(component_manager, "submit_task", _submit_task)

    component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)

    remote_action_supplier(smrb_device_proxy).return_value = (  # type: ignore
        [TaskStatus.QUEUED],
        ["smrb_job_id"],
    )
    remote_action_supplier(recv_device_proxy).return_value = (  # type: ignore
        [TaskStatus.QUEUED],
        ["recv_job_id"],
    )
    remote_action_supplier(dsp_device_proxy).return_value = (  # type: ignore
        [TaskStatus.QUEUED],
        ["dsp_job_id"],
    )

    func = getattr(component_manager, method_name)
    if request_params is not None:
        (status, message) = func(request_params, task_callback=task_callback)
    else:
        (status, message) = func(task_callback=task_callback)

    assert status == TaskStatus.QUEUED
    assert message == "Task queued"

    if request_params is not None:
        if method_name == "scan":
            params_str = request_params
        else:
            params_str = json.dumps(request_params)
        [
            remote_action_supplier(d).assert_called_once_with(params_str)  # type: ignore
            for d in [smrb_device_proxy, recv_device_proxy, dsp_device_proxy]
        ]
    else:
        [
            remote_action_supplier(d).assert_called_once()  # type: ignore
            for d in [smrb_device_proxy, recv_device_proxy, dsp_device_proxy]
        ]

    # need to force an data update
    [
        component_manager._long_running_client._handle_command_completed(job_id)  # type: ignore
        for job_id in ["smrb_job_id", "recv_job_id", "dsp_job_id"]
    ]

    if component_state_callback_params:
        component_state_callback.assert_called_once_with(**component_state_callback_params)  # type: ignore
    else:
        component_state_callback.assert_not_called()  # type: ignore

    calls = [call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)
