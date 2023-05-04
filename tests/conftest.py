"""This module defines elements of the pytest test harness shared by all tests."""
from __future__ import annotations

import collections
import json
import logging
import queue
import sys
import threading
from concurrent import futures
from random import randint
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, cast
from unittest.mock import MagicMock

import grpc
import pytest
import tango
from ska_pst_lmc_proto.ska_pst_lmc_pb2 import StartScanRequest
from ska_pst_lmc_proto.ska_pst_lmc_pb2_grpc import PstLmcServiceServicer, add_PstLmcServiceServicer_to_server
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import CommunicationStatus, ObsState, SimulationMode
from ska_tango_base.executor import TaskStatus
from ska_tango_testing.mock import MockCallable
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DeviceProxy
from tango.test_context import DeviceTestContext, MultiDeviceTestContext, get_host_ip

from ska_pst_lmc.device_proxy import DeviceProxyFactory
from ska_pst_lmc.dsp.dsp_model import DEFAULT_RECORDING_TIME
from ska_pst_lmc.job import DeviceCommandTaskExecutor, TaskExecutor
from ska_pst_lmc.test.test_grpc_server import TestMockServicer, TestPstLmcService
from ska_pst_lmc.util import TelescopeFacilityEnum
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor
from ska_pst_lmc.util.callback import Callback


class _ThreadingCallback:

    mock_callback: MagicMock
    callback_event: threading.Event

    def __init__(self: _ThreadingCallback, is_complete: Optional[Callable[..., bool]] = None):
        self.mock_callback = MagicMock()
        self.callback_event = threading.Event()
        self._is_complete = is_complete or self.is_complete

    def __call__(self: _ThreadingCallback, *args: Any, **kwargs: Any) -> Any:
        self.mock_callback(*args, **kwargs)
        if self._is_complete(*args, **kwargs):
            self.callback_event.set()

    def is_complete(
        self: _ThreadingCallback, *args: Any, status: Optional[TaskStatus] = None, **kwargs: Any
    ) -> bool:
        return status is not None and status == TaskStatus.COMPLETED

    def wait(self: _ThreadingCallback, timeout: Optional[float] = None) -> None:
        self.callback_event.wait(timeout=timeout)

    def clear(self: _ThreadingCallback) -> None:
        self.callback_event.clear()

    def set(self: _ThreadingCallback) -> None:
        self.callback_event.set()

    def __getattr__(self: _ThreadingCallback, name: str) -> Any:
        return getattr(self.mock_callback, name)


class _AttributeEventValidator:
    """Class to validate attribute events between BEAM and subordinate devices."""

    def __init__(
        self: _AttributeEventValidator,
        device_under_test: DeviceProxy,
        source_device_fqdn: str,
        attribute_name: str,
        default_value: Any,
        tango_change_event_helper: TangoChangeEventHelper,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger,
    ) -> None:
        """Initialise validator."""
        self.logger = logger
        self.device_under_test = device_under_test
        self.source_device = DeviceProxyFactory.get_device(source_device_fqdn)
        if attribute_name == "subbandBeamConfiguration":
            self.attribute_name = "channelBlockConfiguration"
        else:
            self.attribute_name = attribute_name
        self.default_value = default_value

        self.attribute_value_queue: queue.Queue[Any] = queue.Queue()
        self.change_event_callbacks = change_event_callbacks

        tango_change_event_helper.subscribe(self.attribute_name)
        self.source_device.subscribe_change_event(attribute_name, self._store_value)

    def _store_value(self: _AttributeEventValidator, value: Any) -> None:
        if self.attribute_name == "channelBlockConfiguration":
            # we need to map from subbandBeamConfiguration
            recv_subband_config = cast(Dict[str, Any], json.loads(value))
            if len(recv_subband_config) == 0:
                value = json.dumps(recv_subband_config)
            else:
                value = json.dumps(calc_expected_beam_channel_block_configuration(recv_subband_config))

        self.attribute_value_queue.put(value)

    def assert_initial_values(self: _AttributeEventValidator) -> None:
        """Assert initial values of BEAM and subordinate device as the same."""

        def _get_values() -> Tuple[Any, Any]:
            beam_value = getattr(self.device_under_test, self.attribute_name)
            if self.attribute_name == "channelBlockConfiguration":
                source_value = getattr(self.source_device, "subbandBeamConfiguration")
            else:
                source_value = getattr(self.source_device, self.attribute_name)

            return beam_value, source_value

        initial_values = _get_values()

        if self.attribute_name != "availableDiskSpace":
            # availableDiskSpace actually changes from a default value a new value when the On command
            # happens
            assert (
                initial_values[0] == self.default_value
            ), f"{self.attribute_name} on {self.device_under_test} not {self.default_value} but {initial_values[0]}"  # noqa: E501
            assert (
                initial_values[1] == self.default_value
            ), f"{self.attribute_name} on {self.device_under_test} not {self.default_value} but {initial_values[1]}"  # noqa: E501

    def assert_values(self: _AttributeEventValidator) -> None:
        """Assert that the events on BEAM as those from subordinate device."""
        # use None as a sentinal value to break out of assertion loop
        try:
            value: Any
            for value in iter(self.attribute_value_queue.get_nowait, None):
                if value is None:
                    break

                self.change_event_callbacks[self.attribute_name].assert_change_event(value, lookahead=3)
        except queue.Empty:
            pass


@pytest.fixture
def default_device_propertry_config() -> Dict[str, Dict[str, Any]]:
    """Get map of default values for device properties."""
    return {
        "test/recv/1": {
            "dataReceiveRate": 0.0,
            "dataReceived": 0,
            "dataDropRate": 0.0,
            "dataDropped": 0,
            "misorderedPackets": 0,
            "misorderedPacketRate": 0.0,
            "malformedPackets": 0,
            "malformedPacketRate": 0.0,
            "misdirectedPackets": 0,
            "misdirectedPacketRate": 0.0,
            "checksumFailurePackets": 0,
            "checksumFailurePacketRate": 0.0,
            "timestampSyncErrorPackets": 0,
            "timestampSyncErrorPacketRate": 0.0,
            "seqNumberSyncErrorPackets": 0,
            "seqNumberSyncErrorPacketRate": 0.0,
            "subbandBeamConfiguration": json.dumps({}),
        },
        "test/dsp/1": {
            "dataRecordRate": 0.0,
            "dataRecorded": 0,
            "availableDiskSpace": sys.maxsize,
            "availableRecordingTime": DEFAULT_RECORDING_TIME,
        },
        "test/smrb/1": {
            "ringBufferUtilisation": 0.0,
        },
    }


@pytest.fixture(scope="module")
def beam_id() -> int:
    """Return beam ID for tests."""
    return 1


@pytest.fixture
def task_executor() -> Generator[TaskExecutor, None, None]:
    """Return a generator for job executor."""
    executor = TaskExecutor()
    executor.start()
    yield executor
    executor.stop()


@pytest.fixture
def device_command_task_executor(task_executor: TaskExecutor) -> DeviceCommandTaskExecutor:
    """Return a generator for a device command job executor."""
    return task_executor._device_task_executor


@pytest.fixture
def csp_configure_scan_request() -> Dict[str, Any]:
    """Return valid configure JSON object that CSP would send."""
    return {
        "interface": "https://schema.skao.int/ska-csp-configure/2.3",
        "common": {
            "config_id": "sbi-mvp01-20200325-00001-science_A",
            "frequency_band": "1",
            "subarray_id": 1,
        },
        "pst": {
            "scan": {
                "activation_time": "2022-01-19T23:07:45Z",
                "bits_per_sample": 32,
                "num_of_polarizations": 2,
                "udp_nsamp": 32,
                "wt_nsamp": 32,
                "udp_nchan": 24,
                "num_frequency_channels": 768,
                "centre_frequency": 1000000000.0,
                "total_bandwidth": 800000000.0,
                "observation_mode": "PULSAR_TIMING",
                "observer_id": "jdoe",
                "project_id": "project1",
                "pointing_id": "pointing1",
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
                "receptor_weights": [1.0],
                "num_rfi_frequency_masks": 1,
                "rfi_frequency_masks": [[1.0, 1.1]],
                "destination_address": ["192.168.178.26", 9021],
                "test_vector_id": "test_vector_id",
                "num_channelization_stages": 1,
                "channelization_stages": [
                    {
                        "num_filter_taps": 1,
                        "filter_coefficients": [1.0],
                        "num_frequency_channels": 10,
                        "oversampling_ratio": [8, 7],
                    }
                ],
            }
        },
    }


@pytest.fixture
def configure_scan_request(
    csp_configure_scan_request: Dict[str, Any], telescope_facility: TelescopeFacilityEnum
) -> Dict[str, Any]:
    """Return a valid configure scan object."""
    # this has been copied from the SKA Telmodel
    # see https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html
    request = {
        **csp_configure_scan_request["common"],
        **csp_configure_scan_request["pst"]["scan"],
    }

    if telescope_facility == TelescopeFacilityEnum.Low:
        request["frequency_band"] = "low"

    return request


@pytest.fixture
def configure_beam_request(configure_scan_request: Dict[str, Any]) -> Dict[str, Any]:
    """Return a valid configure beam object."""
    keys = [
        "num_frequency_channels",
        "num_of_polarizations",
        "bits_per_sample",
        "udp_nsamp",
        "wt_nsamp",
        "udp_nchan",
        "centre_frequency",
        "total_bandwidth",
        "receiver_id",
        "feed_polarization",
        "feed_handedness",
        "feed_angle",
        "feed_tracking_mode",
        "feed_position_angle",
        "receptors",
        "receptor_weights",
        "oversampling_ratio",
    ]

    return {k: configure_scan_request[k] for k in keys}


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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def grpc_endpoint(grpc_port: int) -> str:
    """Return the endpoint of the gRPC server."""
    return f"127.0.0.1:{grpc_port}"


@pytest.fixture(scope="module")
def grpc_servicer(mock_servicer_context: MagicMock, logger: logging.Logger) -> TestMockServicer:
    """Create a test mock servicer given mock context."""
    return TestMockServicer(
        context=mock_servicer_context,
        logger=logger,
    )


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def pst_lmc_service(
    grpc_service: grpc.Server,
    logger: logging.Logger,
) -> Generator[TestPstLmcService, None, None]:
    """Yield an instance of a PstLmcServiceServicer for testing."""
    service = TestPstLmcService(
        grpc_server=grpc_service,
        logger=logger,
    )
    evt = threading.Event()
    service.serve(started_callback=evt.set)
    evt.wait()
    yield service
    service.stop()


@pytest.fixture(scope="module")
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
        server_configuration["timeout"] = 5
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
    return tango_context.device


@pytest.fixture()
def callbacks() -> dict:
    """
    Return a dictionary of callbacks with asynchrony support.

    :return: a collections.defaultdict that returns callbacks by name.
    """
    return collections.defaultdict(MockCallable)


@pytest.fixture
def beam_attribute_names() -> List[str]:
    """Get list of beam change event attributes."""
    return [
        "dataReceiveRate",
        "dataReceived",
        "dataDropRate",
        "dataDropped",
        "misorderedPackets",
        "misorderedPacketRate",
        "malformedPackets",
        "malformedPacketRate",
        "misdirectedPackets",
        "misdirectedPacketRate",
        "checksumFailurePackets",
        "checksumFailurePacketRate",
        "timestampSyncErrorPackets",
        "timestampSyncErrorPacketRate",
        "seqNumberSyncErrorPackets",
        "seqNumberSyncErrorPacketRate",
        "dataRecordRate",
        "dataRecorded",
        "availableDiskSpace",
        "availableRecordingTime",
        "ringBufferUtilisation",
        "channelBlockConfiguration",
    ]


@pytest.fixture()
def additional_change_events_callbacks() -> List[str]:
    """Return additional change event callbacks."""
    return []


@pytest.fixture
def change_event_callback_time() -> float:
    """Get timeout used for change event callbacks."""
    return 1.0


@pytest.fixture
def change_event_callbacks_factory(
    additional_change_events_callbacks: List[str], change_event_callback_time: float
) -> Callable[..., MockTangoEventCallbackGroup]:
    """Get factory to create instances of a `MockTangoEventCallbackGroup`."""

    def _factory() -> MockTangoEventCallbackGroup:
        return MockTangoEventCallbackGroup(
            "longRunningCommandProgress",
            "longRunningCommandStatus",
            "longRunningCommandResult",
            "obsState",
            "healthState",
            *additional_change_events_callbacks,
            timeout=change_event_callback_time,
        )

    return _factory


@pytest.fixture()
def change_event_callbacks(
    change_event_callbacks_factory: Callable[..., MockTangoEventCallbackGroup]
) -> MockTangoEventCallbackGroup:
    """
    Return a dictionary of Tango device change event callbacks with asynchrony support.

    :return: a collections.defaultdict that returns change event
        callbacks by name.
    """
    return change_event_callbacks_factory()


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

        def _handle_evt(*args: Any, **kwargs: Any) -> None:
            self.logger.debug(f"Event recevied with: args={args}, kwargs={kwargs}")
            self.change_event_callbacks[attribute_name](*args, **kwargs)

        subscription_id = self.device_under_test.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            _handle_evt,
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
        self._device = device = tango_change_event_helper.device_under_test

        def _subscribe(property: str) -> None:
            value = getattr(device, property)
            tango_change_event_helper.subscribe(property)
            try:
                # ignore the first event. This should be able to clear out the events
                change_event_callbacks[property].assert_change_event(value)
            except Exception:
                logger.warning(f"Asserting {device}.{property} to be {value} failed.", exc_info=True)

        _subscribe("longRunningCommandProgress")
        _subscribe("longRunningCommandResult")
        _subscribe("longRunningCommandStatus")
        _subscribe("obsState")
        _subscribe("healthState")

        self.change_event_callbacks = change_event_callbacks
        self._logger = logger
        self._tango_change_event_helper = tango_change_event_helper
        self._command_states: Dict[str, str] = {}

    def assert_command(  # noqa: C901 - override checking of complexity for this test
        self: TangoDeviceCommandChecker,
        command: Callable,
        expected_result_code: ResultCode = ResultCode.QUEUED,
        expected_command_result: Optional[str] = '"Completed"',
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
        current_lrc_status = self._device.longRunningCommandStatus
        current_obs_state = self._device.obsState

        if current_lrc_status is None:
            current_lrc_status = ()

        self._logger.info(f"Current longRunningCommandStatus = {current_lrc_status}")

        [[result], [command_id]] = command()
        assert result == expected_result_code

        if expected_command_status_events:
            for expected_command_status in expected_command_status_events:
                while True:
                    expected_lrc_status = (
                        *current_lrc_status,
                        command_id,
                        expected_command_status.name,
                    )
                    self._logger.info(f"Expecting longRunningCommandStatus = {expected_lrc_status}")
                    try:
                        self.change_event_callbacks["longRunningCommandStatus"].assert_change_event(
                            expected_lrc_status
                        )
                        break
                    except Exception as e:
                        # it is possible that the first command has been popped
                        self._logger.info(
                            f"No change event for longRunningCommandStatus = {expected_lrc_status}"
                        )
                        if len(current_lrc_status) >= 2:
                            current_lrc_status = current_lrc_status[2:]
                            self._logger.info(
                                "Removed first 2 items from current_long_running_command_status"
                            )
                            continue

                        current_lrc_status = self._device.longRunningCommandStatus
                        self._logger.exception(
                            f"Unable to assert longRunningCommandStatus. Current value: {current_lrc_status}",
                            exc_info=True,
                        )
                        self._logger.info(
                            f"Currend longRunningCommandResult = {self._device.longRunningCommandResult}"
                        )
                        raise e
        else:
            self.change_event_callbacks["longRunningCommandStatus"].assert_not_called()

        if expected_command_result is not None:
            self.change_event_callbacks["longRunningCommandResult"].assert_change_event(
                (command_id, expected_command_result),
            )

        if expected_obs_state_events and [current_obs_state] != expected_obs_state_events:
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


@pytest.fixture(scope="session")
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
def recv_data_host() -> str:
    """Get network interface for RECV to listen on."""
    return "127.0.0.1"


@pytest.fixture
def subband_udp_ports() -> List[int]:
    """Get UDP port for RECV to listen on."""
    return [randint(20000, 30000) for _ in range(4)]


@pytest.fixture
def subband_monitor_data_callback() -> MagicMock:
    """Create a callback that can be used for subband data monitoring."""
    return MagicMock()


@pytest.fixture
def monitor_data_callback() -> MagicMock:
    """Create fixture for monitor data callback testing."""
    return MagicMock()


@pytest.fixture
def property_callback() -> MagicMock:
    """Create fixture for testing property callbacks."""
    return MagicMock()


@pytest.fixture
def telescope_facility() -> TelescopeFacilityEnum:
    """Get fixture for simulating which telescope facility to test for."""
    return TelescopeFacilityEnum.Low


@pytest.fixture
def device_interface(
    device_name: str,
    beam_id: int,
    grpc_endpoint: str,
    communication_state_callback: Callable[[CommunicationStatus], None],
    component_state_callback: Callable,
    monitor_data_callback: Callable,
    property_callback: Callable,
    telescope_facility: TelescopeFacilityEnum,
) -> MagicMock:
    """Create device interface fixture to mock a Tango device."""
    device_interface = MagicMock()
    device_interface.device_name = device_name
    device_interface.process_api_endpoint = grpc_endpoint
    device_interface.handle_communication_state_change = communication_state_callback
    device_interface.handle_component_state_change = component_state_callback
    device_interface.handle_monitor_data_update = monitor_data_callback
    device_interface.handle_attribute_value_update = property_callback
    device_interface.beam_id = beam_id
    device_interface.facility = telescope_facility

    return device_interface


def calc_expected_beam_channel_block_configuration(recv_subband_config: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate the expected channel block configuration JSON."""
    num_subband = recv_subband_config["common"]["nsubband"]
    subbands = recv_subband_config["subbands"]

    return {
        "num_channel_blocks": num_subband,
        "channel_blocks": [
            {
                "destination_host": subbands[subband_id]["data_host"],
                "destination_port": subbands[subband_id]["data_port"],
                "start_pst_channel": subbands[subband_id]["start_channel"],
                "num_pst_channels": subbands[subband_id]["end_channel"]
                - subbands[subband_id]["start_channel"],
            }
            for subband_id in range(1, num_subband + 1)
        ],
    }


@pytest.fixture
def fail_validate_configure_beam() -> bool:
    """Fixture used to override simulator to fail validation or not."""
    return False


@pytest.fixture
def fail_validate_configure_scan() -> bool:
    """Fixture used to override simulator to fail validation or not."""
    return False
