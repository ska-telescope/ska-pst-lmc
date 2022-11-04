"""This module defines elements of the pytest test harness shared by all tests."""
from __future__ import annotations

import collections
import logging
import threading
import time
from concurrent import futures
from random import randint
from typing import Any, Callable, Dict, Generator, List
from unittest.mock import MagicMock

import grpc
import pytest
import tango
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import StartScanRequest
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceServicer, add_PstLmcServiceServicer_to_server
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState, SimulationMode
from ska_tango_base.executor import TaskStatus
from ska_tango_testing.mock import MockCallable
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DeviceProxy
from tango.test_context import DeviceTestContext, MultiDeviceTestContext, get_host_ip

from ska_pst_lmc.device_proxy import DeviceProxyFactory
from ska_pst_lmc.test.test_grpc_server import TestMockServicer, TestPstLmcService
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.callback import Callback
from ska_pst_lmc.util.job import (
    DEVICE_COMMAND_JOB_EXECUTOR,
    JOB_EXECUTOR,
    DeviceCommandJobExecutor,
    JobExecutor,
)


@pytest.fixture(scope="module")
def beam_id() -> int:
    """Return beam ID for tests."""
    return 1


@pytest.fixture
def configure_beam_request() -> Dict[str, Any]:
    """Return a valid configure beam object."""
    return {
        # CSP JSON fields / PST fields
        "num_frequency_channels": 768,  # nchan
        "num_of_polarizations": 2,  # npol
        "bits_per_sample": 32,  # this is NDIM * NBITS -> ndim == 2
        "udp_nsamp": 32,  # udp_nsamp
        "wt_nsamp": 32,  # wt_nsamp
        "udp_nchan": 24,  # udp_nchan
        "centre_frequency": 1000000000.0,  # frequency
        "total_bandwidth": 800000000,  # bandwidth
        "timing_beam_id": "beam1",  # frontend
        "feed_polarization": "CIRC",  # fd_poln
        "feed_handedness": 1,  # fn_hand
        "feed_angle": 10.0,  # fn_sang
        "feed_tracking_mode": "FA",  # fd_mode
        "feed_position_angle": 0.0,  # fa_req
        "receptors": ["receptor1"],  # antennnas / also nant is the length of this
        "receptor_weights": [1],  # ant_weights
        "oversampling_ratio": [4, 3],  # ovrsamp
    }


@pytest.fixture
def device_command_job_executor() -> Generator[DeviceCommandJobExecutor, None, None]:
    """Return a generator for a device command job executor."""
    DEVICE_COMMAND_JOB_EXECUTOR.start()
    yield DEVICE_COMMAND_JOB_EXECUTOR
    DEVICE_COMMAND_JOB_EXECUTOR.stop()


@pytest.fixture
def job_executor(device_command_job_executor: DeviceCommandJobExecutor) -> Generator[JobExecutor, None, None]:
    """Return a generator for job executor."""
    JOB_EXECUTOR.start()
    yield JOB_EXECUTOR
    JOB_EXECUTOR.stop()


@pytest.fixture
def csp_configure_scan_request(configure_scan_request: Dict[str, Any]) -> Dict[str, Any]:
    """Return valid configure JSON object that CSP would send."""
    return {"common": {}, "pst": {"scan": {**configure_scan_request}}}


@pytest.fixture
def configure_scan_request(scan_id: int) -> Dict[str, Any]:
    """Return a valid configure scan object."""
    # this has been copied from the SKA Telmodel
    # see https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html
    return {
        "activation_time": "2022-01-19T23:07:45Z",
        "timing_beam_id": "beam1",
        "capability": "capability1",
        "scan_id": scan_id,
        "bits_per_sample": 32,
        "num_of_polarizations": 2,
        "udp_nsamp": 32,
        "wt_nsamp": 32,
        "udp_nchan": 24,
        "num_frequency_channels": 768,
        "centre_frequency": 1000000000.0,
        "total_bandwidth": 800000000,
        "observation_mode": "PULSAR_TIMING",
        "observer_id": "jdoe",
        "project_id": "project1",
        "pointing_id": "pointing1",
        "subarray_id": "subarray42",
        "source": "J1921+2153",
        "itrf": [5109360.133, 2006852.586, -3238948.127],
        "receiver_id": "receiver3",
        "feed_polarization": "CIRC",  # fd_poln
        "feed_handedness": 1,  # fn_hand
        "feed_angle": 10.0,  # fn_sang
        "feed_tracking_mode": "FA",  # fd_mode
        "feed_position_angle": 0.0,  # fa_req
        "oversampling_ratio": [4, 3],
        "coordinates": {"ra": "19:21:44.815", "dec": "21.884"},
        "max_scan_length": 10000.5,
        "subint_duration": 30.0,
        "receptors": ["receptor1"],
        "receptor_weights": [1],
        "num_rfi_frequency_masks": 1,
        "rfi_frequency_masks": [[1.0, 1.1]],
        "destination_address": ["192.168.178.26", 9021],
        "test_vector_id": "test_vector_id",
        "pt": {
            "dispersion_measure": 100.0,
            "rotation_measure": 0.0,
            "ephemeris": "",
            "pulsar_phase_predictor": "",
            "output_frequency_channels": 1,
            "output_phase_bins": 64,
            "num_sk_config": 1,
            "sk_config": [{"sk_range": [0.8, 0.9], "sk_integration_limit": 100, "sk_excision_limit": 25.0}],
            "target_snr": 0.0,
        },
    }


@pytest.fixture
def scan_id() -> int:
    """Fixture to generating scan id."""
    return randint(1, 1000)


@pytest.fixture
def scan_request(scan_id: int) -> Dict[str, Any]:
    """Fixture for scan requests."""
    return {"scan_id": scan_id}


@pytest.fixture
def expected_scan_request_protobuf(
    scan_request: Dict[str, Any],
) -> StartScanRequest:
    """Fixture for build expected start_scan request."""
    return StartScanRequest(**scan_request)


@pytest.fixture
def device_properties() -> dict:
    """
    Fixture that returns device_properties to be provided to the device under test.

    This is a default implementation that provides no properties.

    :return: properties of the device under test
    """
    return {}


@pytest.fixture()
def tango_context(
    device_test_config: dict,
) -> Generator[DeviceTestContext, None, None]:
    """Return a Tango test context object, in which the device under test is running."""
    component_manager_patch = device_test_config.pop("component_manager_patch", None)
    if component_manager_patch is not None:
        device_test_config["device"].create_component_manager = component_manager_patch

    if "timeout" not in device_test_config:
        device_test_config["timeout"] = 1
    device_test_config["process"] = True

    tango_context = DeviceTestContext(**device_test_config)
    tango_context.start()
    DeviceProxyFactory._proxy_supplier = tango_context.get_device
    yield tango_context
    tango_context.stop()


@pytest.fixture(scope="class")
def server_configuration() -> dict:
    """Get server configuration for multi device test."""
    return {}


def _generate_port() -> int:
    """Generate a random socket port number."""
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture
def grpc_port() -> int:
    """Fixture to generate port for gRPC."""
    return _generate_port()


@pytest.fixture
def client_id() -> str:
    """Generate a random client_id string."""
    import random
    import string

    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(10))


@pytest.fixture
def device_name(client_id: str) -> str:
    """Generate a random device name."""
    import random

    return f"test/{client_id}/{random.randint(0,16)}"


@pytest.fixture
def grpc_endpoint(grpc_port: int) -> str:
    """Return the endpoint of the gRPC server."""
    return f"127.0.0.1:{grpc_port}"


@pytest.fixture
def grpc_servicer(mock_servicer_context: MagicMock, logger: logging.Logger) -> TestMockServicer:
    """Create a test mock servicer given mock context."""
    return TestMockServicer(
        context=mock_servicer_context,
        logger=logger,
    )


@pytest.fixture
def grpc_service(
    grpc_port: int,
    grpc_servicer: PstLmcServiceServicer,
) -> grpc.Server:
    """Create instance of gRPC server."""
    grpc_tpe = futures.ThreadPoolExecutor(max_workers=10)
    server = grpc.server(grpc_tpe)
    server.add_insecure_port(f"0.0.0.0:{grpc_port}")
    add_PstLmcServiceServicer_to_server(servicer=grpc_servicer, server=server)

    return server


@pytest.fixture
def pst_lmc_service(
    grpc_service: grpc.Server,
    logger: logging.Logger,
) -> Generator[TestPstLmcService, None, None]:
    """Yield an instance of a PstLmcServiceServicer for testing."""
    service = TestPstLmcService(
        grpc_server=grpc_service,
        logger=logger,
    )
    t = threading.Thread(target=service.serve, daemon=True)
    t.start()
    time.sleep(0.5)
    yield service
    service.stop()


@pytest.fixture
def mock_servicer_context() -> MagicMock:
    """Generate a mock gRPC servicer context to use with testing of gRPC calls."""
    return MagicMock()


@pytest.fixture
def multidevice_test_context(
    server_configuration: dict, logger: logging.Logger
) -> Generator[MultiDeviceTestContext, None, None]:
    """Get generator for MultiDeviceTestContext."""
    if "host" not in server_configuration:
        server_configuration["host"] = get_host_ip()
    if "port" not in server_configuration:
        server_configuration["port"] = _generate_port()
    if "timeout" not in server_configuration:
        server_configuration["timeout"] = 1
    if "daemon" not in server_configuration:
        server_configuration["daemon"] = True

    def device_proxy_supplier(fqdn: str, *args: Any, **kwargs: Any) -> tango.DeviceProxy:
        if not fqdn.startswith("tango://"):
            host = server_configuration["host"]
            port = server_configuration["port"]

            fqdn = f"tango://{host}:{port}/{fqdn}#dbase=no"

        return tango.DeviceProxy(fqdn)

    DeviceProxyFactory._proxy_supplier = device_proxy_supplier

    logger.debug(f"Creating multidevice_test_context {server_configuration}")
    with MultiDeviceTestContext(**server_configuration) as context:
        logger.debug("Created multidevice_test_context")
        time.sleep(0.5)
        yield context


@pytest.fixture()
def device_under_test(tango_context: DeviceTestContext) -> DeviceProxy:
    """
    Return a device proxy to the device under test.

    :param tango_context: a Tango test context with the specified device
        running
    :type tango_context: :py:class:`tango.DeviceTestContext`

    :return: a proxy to the device under test
    :rtype: :py:class:`tango.DeviceProxy`
    """
    # Give the PushChanges polled command time to run once.
    time.sleep(0.2)

    return tango_context.device


@pytest.fixture()
def callbacks() -> dict:
    """
    Return a dictionary of callbacks with asynchrony support.

    :return: a collections.defaultdict that returns callbacks by name.
    """
    return collections.defaultdict(MockCallable)


@pytest.fixture()
def change_event_callbacks() -> MockTangoEventCallbackGroup:
    """
    Return a dictionary of Tango device change event callbacks with asynchrony support.

    :return: a collections.defaultdict that returns change event
        callbacks by name.
    """
    return MockTangoEventCallbackGroup(
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
        "obsState",
    )


class TangoChangeEventHelper:
    """Internal testing class used for handling change events."""

    def __init__(
        self: TangoChangeEventHelper,
        device_under_test: DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger,
    ) -> None:
        """Initialise change event helper."""
        self.device_under_test = device_under_test
        self.change_event_callbacks = change_event_callbacks
        self.subscriptions: Dict[str, int] = {}
        self.logger = logger

    def __del__(self: TangoChangeEventHelper) -> None:
        """Free resources held."""
        self.release()

    def subscribe(self: TangoChangeEventHelper, attribute_name: str) -> None:
        """Subscribe to change events of an attribute.

        This returns a :py:class:`MockChangeEventCallback` that can
        then be used to verify changes.
        """
        subscription_id = self.device_under_test.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            self.change_event_callbacks[attribute_name],
        )
        self.logger.debug(f"Subscribed to events of '{attribute_name}'. subscription_id = {subscription_id}")
        self.subscriptions[attribute_name] = subscription_id

    def release(self: TangoChangeEventHelper) -> None:
        """Release any subscriptions that are held."""
        for (name, subscription_id) in self.subscriptions.items():
            self.logger.debug(f"Unsubscribing to '{name}' with subscription_id = {subscription_id}")
            self.device_under_test.unsubscribe_event(subscription_id)
        self.subscriptions.clear()


@pytest.fixture()
def tango_change_event_helper(
    device_under_test: DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
    logger: logging.Logger,
) -> TangoChangeEventHelper:
    """
    Return a helper to simplify subscription to the device under test with a callback.

    :param device_under_test: a proxy to the device under test
    :param change_event_callbacks: dictionary of callbacks with
        asynchrony support, specifically for receiving Tango device
        change events.
    """
    return TangoChangeEventHelper(
        device_under_test=device_under_test,
        change_event_callbacks=change_event_callbacks,
        logger=logger,
    )


class TangoDeviceCommandChecker:
    """A convinence class used to help check a Tango Device command.

    This class can be used to check that a command executed on a
    :py:class:`DeviceProxy` fires the correct change events
    for task status, the completion state, and any changes through
    the :py:class:`ObsState`.
    """

    def __init__(
        self: TangoDeviceCommandChecker,
        tango_change_event_helper: TangoChangeEventHelper,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger,
    ) -> None:
        """Initialise command checker."""
        tango_change_event_helper.subscribe("longRunningCommandProgress")
        change_event_callbacks["longRunningCommandProgress"].assert_change_event(None)

        tango_change_event_helper.subscribe("longRunningCommandResult")
        change_event_callbacks["longRunningCommandResult"].assert_change_event(("", ""))

        tango_change_event_helper.subscribe("longRunningCommandStatus")
        change_event_callbacks["longRunningCommandStatus"].assert_change_event(None)

        tango_change_event_helper.subscribe("obsState")

        self.change_event_callbacks = change_event_callbacks
        self._logger = logger

        self._command_states: Dict[str, str] = {}

    def assert_command(
        self: TangoDeviceCommandChecker,
        command: Callable,
        expected_result_code: ResultCode = ResultCode.QUEUED,
        expected_command_result: str = '"Completed"',
        expected_command_status_events: List[TaskStatus] = [
            TaskStatus.QUEUED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
        ],
        expected_obs_state_events: List[ObsState] = [],
    ) -> None:
        """Assert that the command has the correct result and events.

        This method has sensible defaults of the expected result code,
        the overall result, and the status events that the command
        goes through, and by default asserts that the ObsState model
        doesn't change.

        :param command: a callable on the device proxy.
        :param expected_result_code: the expected result code returned
            from the call. The default is ResultCode.QUEUED.
        :param expected_command_result: the expected command result
            when the command completes. The default is "Completed".
        :param expected_command_status_events: a list of expected
            status events of the command, these should be in the
            order the events happen. Default expected events are:
            [TaskStatus.QUEUED, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        :param expected_obs_state_events: the expected events of the ObsState
            model. The default is an empty list, meaning no events expected.
        """
        [[result], [command_id]] = command()
        assert result == expected_result_code

        if expected_command_status_events:
            for expected_command_status in expected_command_status_events:
                self._command_states[command_id] = expected_command_status.name
                expected_result = tuple([item for kv in self._command_states.items() for item in kv])
                self.change_event_callbacks["longRunningCommandStatus"].assert_change_event(
                    expected_result,
                )

        else:
            self.change_event_callbacks["longRunningCommandStatus"].assert_not_called()

        self.change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (command_id, expected_command_result),
        )

        if expected_obs_state_events:
            for expected_obs_state in expected_obs_state_events:
                self._logger.debug(f"Checking next obsState event is {expected_obs_state.name}")
                self.change_event_callbacks["obsState"].assert_change_event(expected_obs_state.value)
        else:
            self._logger.debug("Checking obsState does not change.")
            self.change_event_callbacks["obsState"].assert_not_called()


@pytest.fixture
def tango_device_command_checker(
    tango_change_event_helper: TangoChangeEventHelper,
    change_event_callbacks: MockTangoEventCallbackGroup,
    logger: logging.Logger,
) -> TangoDeviceCommandChecker:
    """Fixture that returns a TangoChangeEventHelper."""
    return TangoDeviceCommandChecker(
        tango_change_event_helper=tango_change_event_helper,
        change_event_callbacks=change_event_callbacks,
        logger=logger,
    )


@pytest.fixture(scope="module")
def logger() -> logging.Logger:
    """Fixture that returns a default logger for tests."""
    logger = logging.getLogger("TEST_LOGGER")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def abort_event() -> threading.Event:
    """Get fixture to handle aborting threads."""
    return threading.Event()


@pytest.fixture
def stub_background_processing() -> bool:
    """Fixture used to make background processing synchronous."""
    return True


@pytest.fixture
def background_task_processor(
    logger: logging.Logger,
    stub_background_processing: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> BackgroundTaskProcessor:
    """Fixture to create background task processor.

    This can be used in synchronous or background processing if
    a stub_background_processing returns True or False, the default
    is to always stub.
    """
    processor = BackgroundTaskProcessor(default_logger=logger)

    if stub_background_processing:
        # need to stub the submit_task and replace
        logger.debug("Stubbing background processing")

        def _submit_task(
            action_fn: Callable,
            *args: Any,
            **kwargs: Any,
        ) -> MagicMock:
            action_fn()
            return MagicMock()

        monkeypatch.setattr(processor, "submit_task", _submit_task)

    return processor

    return BackgroundTaskProcessor(default_logger=logger)


@pytest.fixture
def communication_state_callback() -> Callable:
    """Create a communication state callback."""
    return MagicMock()


@pytest.fixture
def component_state_callback() -> Callable:
    """Create a component state callback."""
    return MagicMock()


@pytest.fixture
def task_callback() -> Callback:
    """Create a mock component to validate task callbacks."""
    return MagicMock()


@pytest.fixture
def simulation_mode(request: pytest.FixtureRequest) -> SimulationMode:
    """Set simulation mode for test."""
    try:
        return request.param.get("simulation_mode", SimulationMode.TRUE)  # type: ignore
    except Exception:
        return SimulationMode.TRUE


@pytest.fixture
def recv_network_interface() -> str:
    """Get network interface for RECV to listen on."""
    return "0.0.0.0"


@pytest.fixture
def recv_udp_port() -> int:
    """Get UDP port for RECV to listen on."""
    return randint(20000, 30000)


@pytest.fixture
def subband_monitor_data_callback() -> MagicMock:
    """Create a callback that can be used for subband data monitoring."""
    return MagicMock()


@pytest.fixture
def monitor_data_callback() -> MagicMock:
    """Create fixture for monitor data callback testing."""
    return MagicMock()
