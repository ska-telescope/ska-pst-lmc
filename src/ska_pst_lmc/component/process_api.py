# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing the base abstract API for the PST.LMC processes.

This API is not a part of the component manager, as the component manager
is also concerned with callbacks to the TANGO device and has state model
management. This API is expected to be used to call to an external process
or be simulated.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Generator, Optional

from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    BeamConfiguration,
    ConfigureBeamRequest,
    ConfigureScanRequest,
    MonitorData,
    ScanConfiguration,
    StartScanRequest,
)
from ska_tango_base.commands import TaskStatus

from ska_pst_lmc.component.grpc_lmc_client import (
    AlreadyScanningException,
    BaseGrpcException,
    NotConfiguredForScanException,
    NotScanningException,
    PstGrpcLmcClient,
    ResourcesAlreadyAssignedException,
    ResourcesNotAssignedException,
    ScanConfiguredAlreadyException,
)
from ska_pst_lmc.util.background_task import BackgroundTaskProcessor, background_task
from ska_pst_lmc.util.timeout_iterator import TimeoutIterator


class PstProcessApi:
    """Abstract class for the API of the PST.LMC processes like RECV, SMRB, etc."""

    def __init__(
        self: PstProcessApi,
        logger: logging.Logger,
        component_state_callback: Callable,
    ) -> None:
        """Initialise the API.

        :param simulator: the simulator instance to use in the API.
        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        """
        self._logger = logger
        self._component_state_callback = component_state_callback

    def connect(self: PstProcessApi) -> None:
        """Connect to the external process."""
        raise NotImplementedError("PstProcessApi is abstract class")

    def disconnect(self: PstProcessApi) -> None:
        """Disconnect from the external process."""
        raise NotImplementedError("PstProcessApi is abstract class")

    def configure_beam(self: PstProcessApi, resources: Dict[str, Any], task_callback: Callable) -> None:
        """Configure beam for service.

        :param resources: Dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def deconfigure_beam(self: PstProcessApi, task_callback: Callable) -> None:
        """Deconfigure beam to release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def configure_scan(self: PstProcessApi, configuration: Dict[str, Any], task_callback: Callable) -> None:
        """Configure a scan.

        :param configuration: the scan configuration for the device.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def deconfigure_scan(self: PstProcessApi, task_callback: Callable) -> None:
        """Deconfigure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def start_scan(self: PstProcessApi, args: Dict[str, Any], task_callback: Callable) -> None:
        """Start a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def stop_scan(self: PstProcessApi, task_callback: Callable) -> None:
        """Stop a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def abort(self: PstProcessApi, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def reset(self: PstProcessApi, task_callback: Callable) -> None:
        """Reset the component.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def go_to_fault(self: PstProcessApi) -> None:
        """Set remote service in a FAULT state.

        This doesn't take a callback as we want a synchronous call.
        """
        raise NotImplementedError("PstProcessApu is abstract class")

    @background_task
    def monitor(
        self: PstProcessApi,
        subband_monitor_data_callback: Callable[..., None],
        polling_rate: int = 5000,
        monitor_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """Monitor data of remote service.

        This needs to be implemented as a background task

        :param subband_monitor_data_callback: callback to use when there is an
            update of the sub-band monitor data.
        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param monitor_abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring. If not set then the background task
            will create one.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def get_env(self: PstProcessApi) -> Dict[str, Any]:
        """Get the environment properties for the service."""
        raise NotImplementedError("PstProcessApi is abstract class")


class PstProcessApiSimulator(PstProcessApi):
    """Abstract class for the Simulated API of the PST.LMC processes like RECV, SMRB, etc."""

    def __init__(
        self: PstProcessApiSimulator,
        logger: logging.Logger,
        component_state_callback: Callable,
        **kwargs: Any,
    ) -> None:
        """Initialise the API."""
        self._monitor_abort_event = threading.Event()
        self._scanning = False
        super().__init__(logger=logger, component_state_callback=component_state_callback, **kwargs)

    def _should_be_monitoring(self: PstProcessApiSimulator) -> bool:
        if self._monitor_abort_event.is_set():
            return False

        return self._scanning

    def connect(self: PstProcessApiSimulator) -> None:
        """Connect to the external process."""

    def disconnect(self: PstProcessApiSimulator) -> None:
        """Disconnect from the external process."""
        self.stop_monitoring()

    def _simulated_monitor_data_generator(
        self: PstProcessApiSimulator, polling_rate: int
    ) -> Generator[Dict[int, Any], None, None]:
        """Create a generator of simulated monitoring data.

        This is an abstract method.  Subclasses need to implement this.

        :param polling_rate: the rate, in milliseconds, at which the monitoring should generated data.
        """
        raise NotImplementedError("PstProcessApiSimulator is abstract class")

    def go_to_fault(self: PstProcessApiSimulator) -> None:
        """Set simulator into a FAULT state.

        If simulator is scanning then stop scanning.
        """
        if self._scanning:
            self._scanning = False

        self.stop_monitoring()

        self._component_state_callback(obsfault=True)

    @background_task
    def monitor(
        self: PstProcessApiSimulator,
        subband_monitor_data_callback: Callable[..., None],
        polling_rate: int = 5000,
        monitor_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """Monitor data of remote service.

        This needs to be implemented as a background task

        :param subband_monitor_data_callback: callback to use when there is an
            update of the sub-band monitor data.
        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param monitor_abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring. If not set then the background task
            will create one.
        """
        self._logger.debug(f"Starting to monitor at {polling_rate}ms")
        try:
            if monitor_abort_event is not None:
                self._monitor_abort_event = monitor_abort_event
            # make sure we reset the monitoring event
            self._monitor_abort_event.clear()

            while not self._monitor_abort_event.is_set():
                try:
                    for data in TimeoutIterator(
                        self._simulated_monitor_data_generator(polling_rate=polling_rate),
                        abort_event=self._monitor_abort_event,
                        timeout=2 * polling_rate / 1000.0,
                        expected_rate=polling_rate / 1000.0,
                    ):
                        for (subband_id, subband_data) in data.items():
                            subband_monitor_data_callback(subband_id=subband_id, subband_data=subband_data)
                except TimeoutError:
                    if self._monitor_abort_event.is_set():
                        # this could be a race condition for the abort event, so ignore timeout
                        continue
                    self._logger.warning("received timeout during monitoring before abort event set.")

        except Exception:
            self._logger.error("error while monitoring.", exc_info=True)

    def stop_monitoring(self: PstProcessApiSimulator) -> None:
        """Stop the monitoring background thread by setting event."""
        self._monitor_abort_event.set()


class PstProcessApiGrpc(PstProcessApi):
    """Helper class to be used by subclasses of `PstProcessApi` that use gRPC.

    This class should be added as a parent class of gRPC client APIs. Common
    logic of methods can be refactored to this class. This also means that
    requests that have empty request messages can be handled by this class
    specifically. Where request parameters need to be converted to the appropriate
    protobuf message, then subclasses of this class need to implement the
    `_get_<method_name>_request`.

    For monitoring the subclasses have to handle the `_handle_monitor_response`
    method.
    """

    def __init__(
        self: PstProcessApiGrpc,
        client_id: str,
        grpc_endpoint: str,
        logger: logging.Logger,
        component_state_callback: Callable,
        background_task_processor: Optional[BackgroundTaskProcessor] = None,
    ) -> None:
        """Initialise the API.

        :param client_id: the identification of the client, this should be based
            off the FQDN of the MGMT device.
        :param grpc_endpoint: the service endpoint to connect to. As the SMRB.RB
            instances are for each subband this forces this class to be per
            subband.
        :param logger: the logger to use for the API.
        :param component_state_callback: this allows the API to call back to the
            component manager / TANGO device to deal with state model changes.
        :param background_task_processor: an optional background processor that
            will run background tasks like `monitor`.
        """
        logger.info(f"Creating instance of gRPC Process API for '{client_id}'")
        self._client_id = client_id
        self._grpc_client = PstGrpcLmcClient(client_id=client_id, endpoint=grpc_endpoint, logger=logger)
        self._background_task_processor = background_task_processor or BackgroundTaskProcessor(
            default_logger=logger
        )
        self._monitor_abort_event: Optional[threading.Event] = None
        self._connected = False

        super().__init__(logger=logger, component_state_callback=component_state_callback)

    def connect(self: PstProcessApiGrpc) -> None:
        """Connect to the external process.

        Connects to the remote gRPC service. It also establishes a
        """
        self._logger.info("About to call gRPC client connect")
        self._connected = self._grpc_client.connect()

    def disconnect(self: PstProcessApiGrpc) -> None:
        """Disconnect from the external process."""
        if self._monitor_abort_event is not None:
            self._monitor_abort_event.set()

    def _get_configure_beam_request(self: PstProcessApiGrpc, resources: Dict[str, Any]) -> BeamConfiguration:
        """Convert resources dictionary to instance of `BeamConfiguration`."""
        raise NotImplementedError("PstProcessApiGrpc is an abstract class.")

    def _get_configure_scan_request(
        self: PstProcessApiGrpc, configure_parameters: Dict[str, Any]
    ) -> ScanConfiguration:
        """Convert scan parameters dictionary to instance of `ScanConfiguration`."""
        raise NotImplementedError("PstProcessApiGrpc is an abstract class.")

    def _get_start_scan_request(self: PstProcessApiGrpc, scan_parameters: Dict[str, Any]) -> StartScanRequest:
        """Convert scan parameters dictionary to instance of `ScanRequest`.

        For now this is an empty request, however, in the future it is possible that this
        request will have parameters and could be specific to the component.
        """
        return StartScanRequest(**scan_parameters)

    def configure_beam(self: PstProcessApiGrpc, resources: Dict[str, Any], task_callback: Callable) -> None:
        """Configure the beam with the resources.

        :param resources: Dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        self._logger.debug(f"Assigning resources for '{self._client_id}': {resources}")
        task_callback(status=TaskStatus.IN_PROGRESS)

        beam_configuration = self._get_configure_beam_request(resources)
        request = ConfigureBeamRequest(beam_configuration=beam_configuration)
        try:
            self._grpc_client.configure_beam(request=request)

            self._component_state_callback(resourced=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ResourcesAlreadyAssignedException as e:
            self._logger.error(e.message)
            task_callback(result=e.message, status=TaskStatus.FAILED, exception=e)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing configure_beam request for '{self._client_id}'", exc_info=True
            )
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def deconfigure_beam(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Deconfigure the beam, releasing all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            self._grpc_client.deconfigure_beam()

            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ResourcesNotAssignedException as e:
            self._logger.warning(e.message)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result=e.message)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing deconfigure_beam request for '{self._client_id}'", exc_info=True
            )
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def configure_scan(
        self: PstProcessApiGrpc, configuration: Dict[str, Any], task_callback: Callable
    ) -> None:
        """Configure a scan.

        For SMRB this is a no-op command. There is nothing on the server that would be
        performed and executing this will do nothing.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        scan_configuration = self._get_configure_scan_request(configuration)
        request = ConfigureScanRequest(scan_configuration=scan_configuration)
        try:
            self._grpc_client.configure_scan(request)

            self._component_state_callback(configured=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ScanConfiguredAlreadyException as e:
            self._logger.error(e.message)
            task_callback(result=e.message, status=TaskStatus.FAILED, exception=e)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing 'configure' request for '{self._client_id}'", exc_info=True
            )
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def deconfigure_scan(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Deconfigure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            self._grpc_client.deconfigure_scan()

            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except NotConfiguredForScanException as e:
            self._logger.warning(e.message)
            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result=e.message)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing 'deconfigure' request for '{self._client_id}'", exc_info=True
            )
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def start_scan(
        self: PstProcessApiGrpc,
        args: Dict[str, Any],
        task_callback: Callable,
    ) -> None:
        """Start scanning.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        request = self._get_start_scan_request(args)
        try:
            self._grpc_client.start_scan(request)
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except AlreadyScanningException as e:
            self._logger.warning(e.message)
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Problem processing scan request for '{self._client_id}'", exc_info=True)
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def stop_scan(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """End a scan.

        This will call out to the remote service to end a scan.  It will also
        stop monitoring as monitoring is only valid if the service is in a
        scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._stop_monitoring()
            self._grpc_client.stop_scan()
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except NotScanningException as e:
            self._logger.warning(e.message)
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Problem processing stop_scan request for '{self._client_id}'", exc_info=True)
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    @background_task
    def abort(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Abort a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            # stop monitoring if monitoring is happening. This would be the
            # case if our state was SCANNING.
            self._stop_monitoring()
            self._grpc_client.abort()
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Problem in aborting request for '{self._client_id}'", exc_info=True)
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def reset(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Reset service.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._logger.debug(f"About to call reset on {self._grpc_client._client_id} gRPC.")
            self._grpc_client.reset()
            self._component_state_callback(configured=False, resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Error raised while resetting '{self._client_id}'", exc_info=True)
            self.go_to_fault()
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def go_to_fault(self: PstProcessApiGrpc) -> None:
        """Put remote service into FAULT state.

        This is used to put the remote service into a FAULT state to match
        the status of the LMC component.
        """
        try:
            self._component_state_callback(obsfault=True)
            self._grpc_client.go_to_fault()
        except BaseGrpcException:
            self._logger.warn(
                f"Error in trying to put remote service '{self._client_id}' in FAULT state.", exc_info=True
            )

    def get_env(self: PstProcessApiGrpc) -> Dict[str, Any]:
        """Get the environment properties from the remote gRPC service."""
        return self._grpc_client.get_env()

    def _stop_monitoring(self: PstProcessApiGrpc) -> None:
        if self._monitor_abort_event is not None:
            self._monitor_abort_event.set()

    def _handle_monitor_response(
        self: PstProcessApiGrpc, data: MonitorData, monitor_data_callback: Callable[..., None]
    ) -> None:
        """Handle monitoring data response."""
        raise NotImplementedError("PstProcessApiGrpc is abstract.")

    @background_task
    def monitor(
        self: PstProcessApiGrpc,
        subband_monitor_data_callback: Callable[..., None],
        polling_rate: int = 5000,
        monitor_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """Monitor data of remote service.

        :param subband_monitor_data_callback: callback to use when there is an
            update of the sub-band monitor data.
        :param polling_rate: the rate, in milliseconds, at which the monitoring
            should poll. The default value is 5000ms (i.e. 5 seconds).
        :param monitor_abort_event: a :py:class:`threading.Event` that can be
            used to signal to stop monitoring. If not set then the background task
            will create one.
        """
        self._monitor_abort_event = monitor_abort_event or threading.Event()
        try:
            for d in self._grpc_client.monitor(
                polling_rate=polling_rate, abort_event=self._monitor_abort_event
            ):
                self._handle_monitor_response(
                    d.monitor_data, monitor_data_callback=subband_monitor_data_callback
                )
        except Exception:
            self._logger.warning("Error while handing monitoring.", exc_info=True)
        finally:
            # ensure monitor abort event is set
            if not self._monitor_abort_event.is_set():
                self._monitor_abort_event.set()

            self._monitor_abort_event = None
