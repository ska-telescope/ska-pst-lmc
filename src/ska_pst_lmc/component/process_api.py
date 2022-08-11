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
or be simulated. Most of the API is taken from the component manager.
For specifics of the API see
https://developer.skao.int/projects/ska-tango-base/en/latest/api/subarray/component_manager.html
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from ska_pst_lmc_proto.ska_pst_lmc_pb2 import (
    AssignResourcesRequest,
    ConfigureRequest,
    MonitorResponse,
    ScanRequest,
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

    def assign_resources(self: PstProcessApi, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def release_resources(self: PstProcessApi, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def configure(self: PstProcessApi, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def deconfigure(self: PstProcessApi, task_callback: Callable) -> None:
        """Deconfiure a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def scan(self: PstProcessApi, args: dict, task_callback: Callable) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

    def end_scan(self: PstProcessApi, task_callback: Callable) -> None:
        """End a scan.

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

    def restart(self: PstProcessApi, task_callback: Callable) -> None:
        """Perform a restart of the component.

        :param task_callback: callable to connect back to the component manager.
        """
        raise NotImplementedError("PstProcessApi is abstract class")

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

    def _get_assign_resources_request(self: PstProcessApiGrpc, resources: dict) -> AssignResourcesRequest:
        """Convert resources dictionary to instance of `AssignResourcesRequest`."""
        raise NotImplementedError("PstProcessApiGrpc is an abstract class.")

    def _get_configure_scan_request(self: PstProcessApiGrpc, configure_parameters: dict) -> ConfigureRequest:
        """Convert scan parameters dictionary to instance of `ConfigureRequest`."""
        raise NotImplementedError("PstProcessApiGrpc is an abstract class.")

    def _get_scan_request(self: PstProcessApiGrpc, scan_parameters: dict) -> ScanRequest:
        """Convert scan parameters dictionary to instance of `ScanRequest`.

        For now this is an empty request, however, in the future it is possible that this
        request will have parameters and could be specific to the component.
        """
        return ScanRequest(**scan_parameters)

    def assign_resources(self: PstProcessApiGrpc, resources: dict, task_callback: Callable) -> None:
        """Assign resources.

        :param resources: dictionary of resources to allocate.
        :param task_callback: callable to connect back to the component manager.
        """
        self._logger.debug(f"Assigning resources for '{self._client_id}': {resources}")
        task_callback(status=TaskStatus.IN_PROGRESS)

        request = self._get_assign_resources_request(resources)
        try:
            self._grpc_client.assign_resources(request=request)

            self._component_state_callback(resourced=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ResourcesAlreadyAssignedException as e:
            self._logger.error(e.message)
            task_callback(result=e.message, status=TaskStatus.FAILED, exception=e)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing assign_resources request for '{self._client_id}'", exc_info=True
            )
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def release_resources(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Release all resources.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            self._grpc_client.release_resources()

            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ResourcesNotAssignedException as e:
            self._logger.warning(e.message)
            self._component_state_callback(resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result=e.message)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing release_resources request for '{self._client_id}'", exc_info=True
            )
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def configure(self: PstProcessApiGrpc, configuration: dict, task_callback: Callable) -> None:
        """Configure as scan.

        For SMRB this is a no-op command. There is nothing on the server that would be
        performed and executing this will do nothing.

        :param configuration: the configuration of for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        request = self._get_configure_scan_request(configuration)
        try:
            self._grpc_client.configure(request)

            self._component_state_callback(configured=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except ScanConfiguredAlreadyException as e:
            self._logger.error(e.message)
            task_callback(result=e.message, status=TaskStatus.FAILED, exception=e)
        except BaseGrpcException as e:
            self._logger.error(
                f"Problem processing 'configure' request for '{self._client_id}'", exc_info=True
            )
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def deconfigure(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Deconfiure a scan.

        For SMRB this is a no-op command. There is nothin on the server that would be
        performed and executing this will do nothing.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        try:
            self._grpc_client.deconfigure()

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
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def scan(
        self: PstProcessApiGrpc,
        args: dict,
        task_callback: Callable,
    ) -> None:
        """Run a scan.

        :param args: arguments for the scan.
        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)

        request = self._get_scan_request(args)
        try:
            self._grpc_client.scan(request)
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except AlreadyScanningException as e:
            self._logger.warning(e.message)
            self._component_state_callback(scanning=True)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Problem processing scan request for '{self._client_id}'", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def end_scan(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """End a scan.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._stop_monitoring()
            self._grpc_client.end_scan()
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except NotScanningException as e:
            self._logger.warning(e.message)
            self._component_state_callback(scanning=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Problem processing end_scan request for '{self._client_id}'", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

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
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def reset(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Reset service.

        :param task_callback: callable to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._grpc_client.reset()
            self._component_state_callback(configured=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Error raised while resetting '{self._client_id}'", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def restart(self: PstProcessApiGrpc, task_callback: Callable) -> None:
        """Restart service.

        For SMRB we don't restart the actual process. We make sure that the service
        is put into a EMPTY state by first deconfiguring and then releasing resources.

        :param task_callback: callback to connect back to the component manager.
        """
        task_callback(status=TaskStatus.IN_PROGRESS)
        try:
            self._grpc_client.restart()
            self._component_state_callback(configured=False, resourced=False)
            task_callback(status=TaskStatus.COMPLETED, result="Completed")
        except BaseGrpcException as e:
            self._logger.error(f"Error raised while restarting '{self._client_id}'", exc_info=True)
            task_callback(status=TaskStatus.FAILED, result=e.message, exception=e)

    def _stop_monitoring(self: PstProcessApiGrpc) -> None:
        if self._monitor_abort_event is not None:
            self._monitor_abort_event.set()

    def _handle_monitor_response(
        self: PstProcessApiGrpc, data: MonitorResponse, monitor_data_callback: Callable[..., None]
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
                self._handle_monitor_response(d, monitor_data_callback=subband_monitor_data_callback)
        except Exception:
            self._logger.warning("Error while handing monitoring.", exc_info=True)
