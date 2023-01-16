# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains tests for the BEAM component managers class."""

import json
import logging
import sys
from typing import Any, Callable, Dict, Generator, List, Optional, Union, cast
from unittest.mock import ANY, MagicMock, call

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import (
    AdminMode,
    CommunicationStatus,
    HealthState,
    ObsState,
    PowerState,
    SimulationMode,
)
from ska_tango_base.executor import TaskStatus

from ska_pst_lmc.beam import PstBeamComponentManager, PstBeamDeviceInterface
from ska_pst_lmc.device_proxy import DeviceProxyFactory, PstDeviceProxy
from ska_pst_lmc.dsp.dsp_model import DEFAULT_RECORDING_TIME
from ska_pst_lmc.util import TelescopeFacilityEnum
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from tests.conftest import _ThreadingCallback


@pytest.fixture
def smrb_fqdn() -> str:
    """Create SMRB FQDN fixture."""
    return "test/smrb/1"


@pytest.fixture
def smrb_device_proxy(smrb_fqdn: str) -> PstDeviceProxy:
    """Create SMRB Device Proxy fixture."""
    proxy = MagicMock()
    proxy.fqdn = smrb_fqdn
    proxy.__repr__ = MagicMock(return_value=f"PstDeviceProxy('{smrb_fqdn}')")  # type: ignore
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
    proxy.__repr__ = MagicMock(return_value=f"PstDeviceProxy('{recv_fqdn}')")  # type: ignore
    return proxy


@pytest.fixture
def dsp_fqdn() -> str:
    """Create DSP FQDN fixture."""
    return "test/dsp/1"


@pytest.fixture
def dsp_device_proxy(dsp_fqdn: str) -> PstDeviceProxy:
    """Create DSP device proxy fixture."""
    proxy = MagicMock()
    proxy.fqdn = dsp_fqdn
    proxy.__repr__ = MagicMock(return_value=f"PstDeviceProxy('{dsp_fqdn}')")  # type: ignore
    return proxy


@pytest.fixture
def device_proxy(
    device_fqdn: str,
    recv_device_proxy: PstDeviceProxy,
    smrb_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
) -> PstDeviceProxy:
    """Create a generic device proxy fixture."""
    if recv_device_proxy.fqdn == device_fqdn:
        return recv_device_proxy
    elif smrb_device_proxy.fqdn == device_fqdn:
        return smrb_device_proxy
    elif dsp_device_proxy.fqdn == device_fqdn:
        return dsp_device_proxy
    else:
        proxy = MagicMock()
        proxy.fqdn = device_fqdn
        proxy.__repr__ = MagicMock(return_value=f"PstDeviceProxy('{device_fqdn}')")  # type: ignore
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
def patch_submit_job() -> bool:
    """Patch submit_job."""
    return False


@pytest.fixture
def device_interface(
    device_name: str,
    beam_id: int,
    smrb_fqdn: str,
    recv_fqdn: str,
    dsp_fqdn: str,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    property_callback: Callable,
    telescope_facility: TelescopeFacilityEnum,
) -> PstBeamDeviceInterface:
    """Create device interface fixture to mock the BEAM.MGMT tango device."""
    device_interface = MagicMock()
    device_interface.smrb_fqdn = smrb_fqdn
    device_interface.recv_fqdn = recv_fqdn
    device_interface.dsp_fqdn = dsp_fqdn
    device_interface.device_name = device_name
    device_interface.handle_communication_state_change = communication_state_callback
    device_interface.handle_component_state_change = component_state_callback
    device_interface.handle_attribute_value_update = property_callback
    device_interface.beam_id = beam_id
    device_interface.facility = telescope_facility

    return cast(PstBeamDeviceInterface, device_interface)


@pytest.fixture
def component_manager(
    device_interface: PstBeamDeviceInterface,
    smrb_fqdn: str,
    recv_fqdn: str,
    dsp_fqdn: str,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
    logger: logging.Logger,
    background_task_processor: BackgroundTaskProcessor,
    monkeypatch: pytest.MonkeyPatch,
    patch_submit_job: bool,
) -> Generator[PstBeamComponentManager, None, None]:
    """Create PST Beam Component fixture."""

    def _get_device(fqdn: str) -> PstDeviceProxy:
        if fqdn == smrb_fqdn:
            return smrb_device_proxy
        elif fqdn == recv_fqdn:
            return recv_device_proxy
        elif fqdn == dsp_fqdn:
            return dsp_device_proxy
        else:
            raise ValueError(f"Unexpected fqdn {fqdn}")

    monkeypatch.setattr(DeviceProxyFactory, "get_device", _get_device)

    component_manager = PstBeamComponentManager(
        device_interface=device_interface,
        logger=logger,
        background_task_processor=background_task_processor,
    )

    if patch_submit_job:
        from ska_pst_lmc.beam.beam_component_manager import _RemoteJob
        from ska_pst_lmc.util.callback import Callback

        def _remote_job_call(
            remote_job: _RemoteJob, *args: None, task_callback: Callback, **kwargs: Any
        ) -> None:
            remote_job._completion_callback(task_callback)  # type: ignore

        def _submit_task(job: Callable, *args: Any, task_callback: Callback, **kwargs: Any) -> None:
            job(task_callback=task_callback)

        monkeypatch.setattr(component_manager, "submit_task", _submit_task)
        monkeypatch.setattr(_RemoteJob, "__call__", _remote_job_call)

    yield component_manager
    component_manager._pst_task_executor.stop()


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
def test_beam_cm_handle_communication_state_change(
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


def test_beam_cm_delegates_admin_mode(
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


def test_beam_cm_calls_abort_on_subdevices(
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
    csp_configure_scan_request: Dict[str, Any],
    scan_request: Dict[str, Any],
) -> Optional[Any]:
    """Get request parameters for a given method name."""
    if method_name == "configure_scan":
        return csp_configure_scan_request
    elif method_name == "scan":
        return int(scan_request["scan_id"])
    elif method_name == "go_to_fault":
        return "putting BEAM into fault"
    else:
        return None


@pytest.mark.parametrize(
    "method_name, remote_commands, component_state_callback_params",
    [
        ("on", "On", {"power": PowerState.ON}),
        ("off", "Off", {"power": PowerState.OFF}),
        ("reset", "Reset", {"power": PowerState.OFF}),
        ("standby", "Standby", {"power": PowerState.STANDBY}),
        (
            "configure_scan",
            ["ConfigureBeam", "ConfigureScan"],
            {"configured": True},
        ),
        (
            "deconfigure_scan",
            ["DeconfigureBeam", "DeconfigureScan"],
            {"configured": False},
        ),
        ("scan", "Scan", {"scanning": True}),
        ("end_scan", "EndScan", {"scanning": False}),
        (
            "obsreset",
            ["ObsReset", "DeconfigureBeam"],
            {"configured": False},
        ),
        ("go_to_fault", "GoToFault", {"obsfault": True}),
    ],
)
def test_beam_cm_remote_actions(  # noqa: C901 - override checking of complexity for this test
    component_manager: PstBeamComponentManager,
    device_interface: MagicMock,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
    component_state_callback: Callable,
    method_name: str,
    request_params: Optional[Any],
    remote_commands: Union[str, List[str]],
    component_state_callback_params: Optional[dict],
) -> None:
    """Assert that actions that need to be delegated to remote devices."""
    if method_name == "obsreset":
        smrb_device_proxy.obsState = ObsState.ABORTED
        recv_device_proxy.obsState = ObsState.ABORTED
        dsp_device_proxy.obsState = ObsState.ABORTED

    task_callback = _ThreadingCallback()

    component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)

    if type(remote_commands) is not list:
        remote_commands = [remote_commands]  # type: ignore

    [
        setattr(  # type: ignore
            d, m, MagicMock(name=f"{d}.{m}", return_value=([ResultCode.OK], ["Completed"]))
        )
        for d in component_manager._remote_devices
        for m in remote_commands
    ]

    func = getattr(component_manager, method_name)
    if request_params is not None:
        (status, message) = func(request_params, task_callback=task_callback)
    else:
        (status, message) = func(task_callback=task_callback)

    assert status == TaskStatus.QUEUED
    assert message == "Task queued"

    task_callback.wait()

    if request_params is not None:
        if method_name == "scan":
            params_str = str(request_params)
        if method_name == "go_to_fault":
            params_str = str(request_params)
        elif method_name == "configure_scan":
            # ensure we use a the common and pst scan configuration
            scan_configuration = {**request_params["common"], **request_params["pst"]["scan"]}

            params_str = json.dumps(scan_configuration)
        else:
            params_str = json.dumps(request_params)
        [
            getattr(d, m).assert_called_once_with(params_str)  # type: ignore
            for d in component_manager._remote_devices
            for m in remote_commands
        ]
    else:
        [
            getattr(d, m).assert_called_once()  # type: ignore
            for d in component_manager._remote_devices
            for m in remote_commands
        ]

    if component_state_callback_params:
        component_state_callback.assert_called_once_with(**component_state_callback_params)  # type: ignore
    else:
        component_state_callback.assert_not_called()  # type: ignore

    calls = [call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)
    if method_name == "go_to_fault":
        device_interface.handle_fault.assert_called_once_with(fault_msg="putting BEAM into fault")

    if method_name == "obsreset":
        cast(MagicMock, device_interface.update_health_state).assert_called_once_with(
            health_state=HealthState.OK
        )
    else:
        cast(MagicMock, device_interface.update_health_state).assert_not_called()


@pytest.mark.parametrize(
    "property_name, device_fqdn, device_attr_name, initial_value, update_value",
    [
        ("data_receive_rate", "test/recv/1", "dataReceiveRate", 0.0, 12.3),
        ("data_received", "test/recv/1", "dataReceived", 0, 1138),
        ("data_drop_rate", "test/recv/1", "dataDropRate", 0.1, 0.3),
        ("data_dropped", "test/recv/1", "dataDropped", 1, 11),
        ("data_record_rate", "test/dsp/1", "dataRecordRate", 0.2, 52.3),
        ("data_recorded", "test/dsp/1", "dataRecorded", 2, 42),
        ("available_disk_space", "test/dsp/1", "availableDiskSpace", sys.maxsize, 1235),
        ("available_recording_time", "test/dsp/1", "availableRecordingTime", DEFAULT_RECORDING_TIME, 9876.0),
        ("ring_buffer_utilisation", "test/smrb/1", "ringBufferUtilisation", 0.0, 12.5),
    ],
)
def test_beam_cm_monitor_attributes(
    component_manager: PstBeamComponentManager,
    property_name: str,
    device_proxy: PstDeviceProxy,
    device_attr_name: str,
    initial_value: Any,
    update_value: Any,
    property_callback: Callable,
) -> None:
    """Test that component manager subscribes to monitoring events."""
    # ensure subscriptions
    component_manager._subscribe_change_events()

    setattr(component_manager, property_name, initial_value)

    subscription_callbacks = [
        cal.kwargs["callback"]
        for cal in cast(MagicMock, device_proxy.subscribe_change_event).call_args_list
        if cal.kwargs["attribute_name"] == device_attr_name
    ]

    assert len(subscription_callbacks) == 1

    # get the callback
    callback = subscription_callbacks[0]

    # execute callback to ensure we make the value get updated
    callback(update_value)

    assert getattr(component_manager, property_name) == update_value

    # still need worry about the event callback to TANGO device
    cast(MagicMock, property_callback).assert_called_with(property_name, update_value)


def test_beam_cm_channel_block_configuration(
    component_manager: PstBeamComponentManager,
    recv_device_proxy: PstDeviceProxy,
    property_callback: Callable,
) -> None:
    """Test that component manager handles channel block configuration from RECV subband configuration."""
    component_manager._subscribe_change_events()

    component_manager.channel_block_configuration = {}

    subscription_callbacks = [
        cal.kwargs["callback"]
        for cal in cast(MagicMock, recv_device_proxy.subscribe_change_event).call_args_list
        if cal.kwargs["attribute_name"] == "subbandBeamConfiguration"
    ]

    assert len(subscription_callbacks) == 1

    # get the callback
    callback = subscription_callbacks[0]

    # execute callback to ensure empty resources will be handled correctly
    callback("{}")

    assert component_manager.channel_block_configuration == {}

    # still need worry about the event callback to TANGO device
    cast(MagicMock, property_callback).assert_called_with("channel_block_configuration", "{}")

    callback(
        json.dumps(
            {
                "common": {"nsubband": 2},
                "subbands": {
                    1: {
                        "data_host": "10.10.0.1",
                        "data_port": 30000,
                        "start_channel": 0,
                        "end_channel": 10,
                    },
                    2: {
                        "data_host": "10.10.0.1",
                        "data_port": 30001,
                        "start_channel": 10,
                        "end_channel": 16,
                    },
                },
            }
        )
    )

    expected_channel_block_configuration = {
        "num_channel_blocks": 2,
        "channel_blocks": [
            {"data_host": "10.10.0.1", "data_port": 30000, "start_channel": 0, "num_channels": 10},
            {"data_host": "10.10.0.1", "data_port": 30001, "start_channel": 10, "num_channels": 6},
        ],
    }

    assert component_manager.channel_block_configuration == expected_channel_block_configuration
    cast(MagicMock, property_callback).assert_called_with(
        "channel_block_configuration", json.dumps(expected_channel_block_configuration)
    )


def test_beam_cm_monitor_subscription_lifecycle(
    component_manager: PstBeamComponentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the BEAM component manager subscribes/unsubscribes to monitoring events."""
    # Patch the component manager to a) not use background processing,
    # b) spy on some methods to check if called.

    def _submit_job(
        *args: Any, task_callback: Callable, completion_callback: Callable, **kwargs: Any
    ) -> None:
        completion_callback(task_callback)

    monkeypatch.setattr(component_manager, "_submit_remote_job", _submit_job)

    subscribe_change_events_spy = MagicMock(wraps=component_manager._subscribe_change_events)
    monkeypatch.setattr(component_manager, "_subscribe_change_events", subscribe_change_events_spy)

    unsubscribe_change_events_spy = MagicMock(wraps=component_manager._unsubscribe_change_events)
    monkeypatch.setattr(component_manager, "_unsubscribe_change_events", unsubscribe_change_events_spy)

    # when created the component manager has no subscriptions
    assert len(component_manager._change_event_subscriptions) == 0

    # call On
    component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)
    component_manager.on(task_callback=MagicMock())

    # check that the monitoring event subscriptions were set up.
    subscribe_change_events_spy.assert_called_once()
    assert len(component_manager._change_event_subscriptions) > 0

    # call off
    component_manager.off(task_callback=MagicMock())

    # check that the monitoring event subscriptions were stopped.
    unsubscribe_change_events_spy.assert_called_once()
    assert len(component_manager._change_event_subscriptions) == 0


@pytest.mark.parametrize("patch_submit_job", [True])
def test_beam_cm_stores_config_id(
    component_manager: PstBeamComponentManager,
    csp_configure_scan_request: Dict[str, Any],
) -> None:
    """Test to see the BEAM component manager sets config id configure/deconfigure scan."""
    task_callback = MagicMock()

    assert component_manager.config_id == ""

    component_manager.configure_scan(csp_configure_scan_request, task_callback=task_callback)

    # assert current scan config is configure_scan request
    assert component_manager.config_id == csp_configure_scan_request["common"]["config_id"]

    component_manager.deconfigure_scan(task_callback=task_callback)
    assert component_manager.config_id == ""


@pytest.mark.parametrize("patch_submit_job", [True])
def test_beam_cm_configure_scan_sets_expected_data_record_rate(
    component_manager: PstBeamComponentManager,
    csp_configure_scan_request: Dict[str, Any],
) -> None:
    """Test to BEAM component manager updates expected data rate on configure/deconfigure scan."""
    from ska_pst_lmc.dsp.dsp_util import generate_dsp_scan_request

    task_callback = _ThreadingCallback()

    dsp_scan_request = generate_dsp_scan_request(csp_configure_scan_request["pst"]["scan"])

    assert component_manager.expected_data_record_rate == 0.0

    component_manager.configure_scan(configuration=csp_configure_scan_request, task_callback=task_callback)

    assert component_manager.expected_data_record_rate == dsp_scan_request["bytes_per_second"]

    component_manager.deconfigure_scan(task_callback=task_callback)

    assert component_manager.expected_data_record_rate == 0.0


@pytest.mark.parametrize("patch_submit_job", [True])
def test_beam_cm_updates_scan_id_on_start_scan_stop_scan(
    component_manager: PstBeamComponentManager, scan_id: int
) -> None:
    """Test to BEAM component manager updates scan_id on start_scan/end_scan."""
    task_callback = MagicMock()

    assert component_manager.scan_id == 0

    component_manager.start_scan({"scan_id": scan_id}, task_callback=task_callback)

    assert component_manager.scan_id == scan_id

    component_manager.stop_scan(task_callback=task_callback)

    assert component_manager.scan_id == 0


def test_beam_cm_set_simulation_mode_on_child_devices(
    component_manager: PstBeamComponentManager,
    smrb_device_proxy: PstDeviceProxy,
    recv_device_proxy: PstDeviceProxy,
    dsp_device_proxy: PstDeviceProxy,
) -> None:
    """Test component manager delegates setting simulation mode to sub-component devices."""
    component_manager.simulation_mode = SimulationMode.FALSE

    assert smrb_device_proxy.simulationMode == SimulationMode.FALSE
    assert recv_device_proxy.simulationMode == SimulationMode.FALSE
    assert dsp_device_proxy.simulationMode == SimulationMode.FALSE

    component_manager.simulation_mode = SimulationMode.TRUE

    assert smrb_device_proxy.simulationMode == SimulationMode.TRUE
    assert recv_device_proxy.simulationMode == SimulationMode.TRUE
    assert dsp_device_proxy.simulationMode == SimulationMode.TRUE


@pytest.mark.parametrize("device_fqdn", ["test/smrb/1", "test/recv/1", "test/dsp/1"])
def test_beam_cm_faults_when_a_subordinated_device_faults(
    component_manager: PstBeamComponentManager,
    device_fqdn: str,
    device_proxy: PstDeviceProxy,
    device_interface: PstBeamDeviceInterface,
) -> None:
    """Test when a subordinate device faults that PstBeam is notified."""
    component_manager._subscribe_change_events()

    # assert that we subscribe to obsState
    subscription_callbacks = [
        cal.kwargs["callback"]
        for cal in cast(MagicMock, device_proxy.subscribe_change_event).call_args_list
        if cal.kwargs["attribute_name"] == "obsState"
    ]

    assert len(subscription_callbacks) == 1

    # get the callback
    subscription_callbacks[0]
    callback: Callable = subscription_callbacks[0]

    # if obsState is FAULT - get current fault message from subordinate
    for obs_state in ObsState:
        # want to ignore FAULT so we can assert there has been not update
        # on the device itself when a fault happens.
        if obs_state == ObsState.FAULT:
            continue

        callback(obs_state)

    cast(MagicMock, device_interface).handle_subdevice_fault.assert_not_called()

    callback(ObsState.FAULT)
    cast(MagicMock, device_interface).handle_subdevice_fault.assert_called_once_with(
        device_fqdn=device_fqdn, fault_msg=ANY
    )


@pytest.mark.parametrize("device_fqdn", ["test/smrb/1", "test/recv/1", "test/dsp/1"])
def test_beam_cm_propagates_subordinate_device_error_messages_on_faults(
    component_manager: PstBeamComponentManager,
    device_proxy: PstDeviceProxy,
    device_interface: PstBeamDeviceInterface,
) -> None:
    """Test last fault message propagates."""
    component_manager._subscribe_change_events()

    cast(MagicMock, device_proxy).healthFailureMessage = "test error message"

    # assert that we subscribe to obsState
    subscription_callbacks = [
        cal.kwargs["callback"]
        for cal in cast(MagicMock, device_proxy.subscribe_change_event).call_args_list
        if cal.kwargs["attribute_name"] == "obsState"
    ]

    assert len(subscription_callbacks) == 1

    # get the callback
    subscription_callbacks[0]
    callback: Callable = subscription_callbacks[0]

    # if obsState is FAULT - get current fault message from subordinate
    # assert that BEAM gets notified of the fault state
    callback(ObsState.FAULT)
    cast(MagicMock, device_interface).handle_subdevice_fault.assert_called_once_with(
        device_fqdn=ANY, fault_msg="test error message"
    )


@pytest.mark.parametrize("telescope_facility", [TelescopeFacilityEnum.Low, TelescopeFacilityEnum.Mid])
def test_beam_cm_removes_frequency_band_only_for_low(
    component_manager: PstBeamComponentManager,
    csp_configure_scan_request: Dict[str, Any],
    configure_scan_request: Dict[str, Any],
    telescope_facility: TelescopeFacilityEnum,
) -> None:
    """Test that component manager removes frequency band for Low but not High."""
    expected_scan_request_str = json.dumps(configure_scan_request)
    assert "frequency_band" in csp_configure_scan_request["common"]
    if telescope_facility == TelescopeFacilityEnum.Low:
        assert "frequency_band" not in configure_scan_request
    else:
        assert "frequency_band" in configure_scan_request

    task_callback = _ThreadingCallback()

    component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)

    [
        setattr(  # type: ignore
            d, m, MagicMock(name=f"{d}.{m}", return_value=([ResultCode.OK], ["Completed"]))
        )
        for d in component_manager._remote_devices
        for m in ["ConfigureScan", "ConfigureBeam"]
    ]

    component_manager.configure_scan(configuration=csp_configure_scan_request, task_callback=task_callback)

    task_callback.wait()

    [
        getattr(d, m).assert_called_once_with(expected_scan_request_str)  # type: ignore
        for d in component_manager._remote_devices
        for m in ["ConfigureScan", "ConfigureBeam"]
    ]

    calls = [call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)


def test_beam_cm_start_communicating(
    component_manager: PstBeamComponentManager,
    device_interface: PstBeamDeviceInterface,
) -> None:
    """Test BEAM component manager when start_communicating is called."""
    component_manager._communication_state = CommunicationStatus.DISABLED
    component_manager.start_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(health_state=HealthState.OK)
    assert component_manager._communication_state == CommunicationStatus.ESTABLISHED


def test_beam_cm_stop_communicating(
    component_manager: PstBeamComponentManager,
    device_interface: PstBeamDeviceInterface,
) -> None:
    """Test BEAM component manager when stop_communicating is called."""
    component_manager._communication_state = CommunicationStatus.ESTABLISHED
    component_manager.stop_communicating()

    cast(MagicMock, device_interface.update_health_state).assert_called_once_with(
        health_state=HealthState.UNKNOWN
    )
    assert component_manager._communication_state == CommunicationStatus.DISABLED


@pytest.mark.parametrize(
    "device_fqdn, beam_obs_state, subdevice_obs_state",
    [
        ("test/smrb/1", ObsState.ABORTED, ObsState.SCANNING),
        ("test/recv/1", ObsState.ABORTED, ObsState.READY),
        ("test/dsp/1", ObsState.ABORTED, ObsState.IDLE),
        ("test/smrb/1", ObsState.FAULT, ObsState.IDLE),
        ("test/recv/1", ObsState.FAULT, ObsState.SCANNING),
        ("test/dsp/1", ObsState.FAULT, ObsState.READY),
        ("test/smrb/1", ObsState.ABORTED, ObsState.EMPTY),
        ("test/recv/1", ObsState.ABORTED, ObsState.EMPTY),
        ("test/dsp/1", ObsState.ABORTED, ObsState.EMPTY),
        ("test/smrb/1", ObsState.FAULT, ObsState.EMPTY),
        ("test/recv/1", ObsState.FAULT, ObsState.EMPTY),
        ("test/dsp/1", ObsState.FAULT, ObsState.EMPTY),
    ],
)
def test_beam_cm_puts_subordinate_devices_in_state_to_do_obsreset(
    component_manager: PstBeamComponentManager,
    device_proxy: PstDeviceProxy,
    device_fqdn: str,
    beam_obs_state: ObsState,
    subdevice_obs_state: ObsState,
) -> None:
    """Test that obsreset puts subordinate devices in right state before resetting."""
    for d in component_manager._remote_devices:
        if d.fqdn == device_proxy.fqdn:
            d.obsState = subdevice_obs_state
        else:
            d.obsState = beam_obs_state

    task_callback = _ThreadingCallback()

    component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)

    [
        setattr(  # type: ignore
            d, m, MagicMock(name=f"{d}.{m}", return_value=([ResultCode.OK], ["Completed"]))
        )
        for d in component_manager._remote_devices
        for m in ["Abort", "ObsReset", "DeconfigureBeam"]
    ]

    component_manager.obsreset(task_callback=task_callback)

    task_callback.wait()

    if subdevice_obs_state != ObsState.EMPTY:
        cast(MagicMock, device_proxy).Abort.assert_called_once()

    [
        cast(MagicMock, d).Abort.assert_not_called()  # type: ignore
        for d in component_manager._remote_devices
        if d.fqdn != device_fqdn
    ]

    [
        getattr(d, m).assert_called_once()  # type: ignore
        for d in component_manager._remote_devices
        for m in ["ObsReset", "DeconfigureBeam"]
        if d.fqdn != device_fqdn or subdevice_obs_state != ObsState.EMPTY
    ]

    calls = [call(status=TaskStatus.COMPLETED, result="Completed")]
    task_callback.assert_has_calls(calls)
