# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the BEAM component managers class."""

import json
import logging
from typing import Callable, List, Optional
from unittest.mock import MagicMock, call

import pytest
from ska_tango_base.control_model import AdminMode, CommunicationStatus, PowerState, SimulationMode
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.beam.beam_component_manager import PstBeamComponentManager, _PstBeamTask
from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.remote_task import AggregateRemoteTask


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
    logger: logging.Logger,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    background_task_processor: BackgroundTaskProcessor,
    monkeypatch: pytest.MonkeyPatch,
) -> PstBeamComponentManager:
    """Create PST Beam Component fixture."""
    smrb_fqdn = smrb_device_proxy.fqdn
    recv_fqdn = recv_device_proxy.fqdn

    def _get_device(fqdn: str) -> PstDeviceProxy:
        if fqdn == smrb_fqdn:
            return smrb_device_proxy
        else:
            return recv_device_proxy

    monkeypatch.setattr(DeviceProxyFactory, "get_device", _get_device)

    return PstBeamComponentManager(
        smrb_fqdn,
        recv_fqdn,
        SimulationMode.TRUE,
        logger,
        communication_state_callback,
        component_state_callback,
        background_task_processor=background_task_processor,
    )


def test_beam_task(
    smrb_device_proxy: PstDeviceProxy, recv_device_proxy: PstDeviceProxy, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test logic of _PstBeamTask."""
    remote_task = MagicMock()
    add_remote_task = MagicMock()
    action = MagicMock()
    task_callback = MagicMock()

    monkeypatch.setattr(AggregateRemoteTask, "__call__", remote_task)
    monkeypatch.setattr(AggregateRemoteTask, "add_remote_task", add_remote_task)

    task = _PstBeamTask(
        action=action,
        devices=[smrb_device_proxy, recv_device_proxy],
        task_callback=task_callback,
    )

    assert task._task is not None
    assert task._task.task_callback == task_callback

    add_remote_task.call_count == 2
    calls = [call(device=smrb_device_proxy, action=action), call(device=recv_device_proxy, action=action)]
    add_remote_task.assert_has_calls(calls)

    task()

    remote_task.assert_called_once()


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
) -> None:
    """Test component manager delegates setting admin mode to sub-element devices."""
    for a in list(AdminMode):
        component_manager.update_admin_mode(a)

        assert smrb_device_proxy.adminMode == a
        assert recv_device_proxy.adminMode == a


def test_component_manager_assign(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'assign' method correctly."""
    task_callback = MagicMock()

    resources = {"foo": "bar"}
    resources_str = json.dumps(resources)

    (status, message) = component_manager.assign(resources=resources, task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "Resourcing"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.AssignResources.assert_called_once_with(resources_str)


def test_component_manager_release(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'release' method correctly."""
    task_callback = MagicMock()

    resources = {"foo": "bar"}
    resources_str = json.dumps(resources)

    (status, message) = component_manager.release(resources=resources, task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "Releasing"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.ReleaseResources.assert_called_once_with(resources_str)


def test_component_manager_release_all(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'release_all' method correctly."""
    task_callback = MagicMock()

    (status, message) = component_manager.release_all(task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "Releasing all"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.ReleaseAllResources.assert_called_once()


def test_component_manager_configure(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'configure' method correctly."""
    task_callback = MagicMock()

    configuration = {"cat": "dogs"}
    configuration_str = json.dumps(configuration)

    (status, message) = component_manager.configure(configuration=configuration, task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "Configuring"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.Configure.assert_called_once_with(configuration_str)


def test_component_manager_deconfigure(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'deconfigure' method correctly."""
    task_callback = MagicMock()

    (status, message) = component_manager.deconfigure(task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "Deconfiguring"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.End.assert_called_once()


def test_component_manager_scan(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'scan' method correctly."""
    task_callback = MagicMock()

    args = {"luke": "skywalker"}
    args_str = json.dumps(args)

    (status, message) = component_manager.scan(args=args, task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "Scanning"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.Scan.assert_called_once_with(args_str)


def test_component_manager_end_scan(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'end_scan' method correctly."""
    task_callback = MagicMock()

    (status, message) = component_manager.end_scan(task_callback=task_callback)
    assert status == TaskStatus.QUEUED
    assert message == "End scanning"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.EndScan.assert_called_once()


def test_component_manager_abort(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    background_task_processor: BackgroundTaskProcessor,
) -> None:
    """Test component manager handles the 'abort' method correctly."""
    task_callback = MagicMock()

    (status, message) = component_manager.abort(task_callback=task_callback)
    assert status == TaskStatus.IN_PROGRESS
    assert message == "Aborting"

    [call1] = background_task_processor.submit_task.call_args_list  # type: ignore
    task = call1.args[0]

    assert task._devices == [smrb_device_proxy, recv_device_proxy]
    assert task._task_callback == task_callback
    remote_tasks = task._task.tasks

    for (d, t) in zip(task._devices, remote_tasks):
        t.action(d)
        d.Abort.assert_called_once()
