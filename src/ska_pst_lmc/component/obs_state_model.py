# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This modue provides the PST overrides of the ObsStateModel.

There is known tech debt in PST in regards to the fact that it
was initially developed using a sub-array model and not an
obs device. While the BEAM.MGMT uses a `CspSubElementObsStateModel`
and `CspSubElementObsStateMachine` this does not work for the
sub-devices like SMRB.MGMT, RECV.MGMT, and DSP.MGMT which still
have a resourcing step and a configuring step. To simplify the
resetting as part of AT3-425 the default ObsStateMachine needs
to be overriden to allow for the "unresourced" (sic - SKA term)
state.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from transitions.extensions import LockedMachine as Machine


class PstObsStateMachine(Machine):
    """
    State machine for observation state.

    This class to be used in place of the
    :py:class:`ska_control_model._ObsStateMachine` state machine
    to allow for the specifics of the state machine needed for the
    PST Process sub-devices (i.e. SMRB.MGMT, DSP.MGMT, RECV.MGMT, etc)

    This is based off the `SKA ObsStateModel
    <https://developer.skao.int/projects/ska-control-model/en/latest/obs_state.html#ska_control_model.ObsStateModel>`_

    The full list of supported states are:

    * **EMPTY**: the PST subdevice has no configuration
    * **RESOURCING_EMPTY**: the PST subdevice is unresourced, but performing
      a configure beam operation
    * **RESOURCING_IDLE**: the PST subdevice is beam configured, and is currently
      finishing the configure beam operation
    * **IDLE**: the PST subdevice is beam configured but not scan configured
    * **CONFIGURING_IDLE**: the PST subdevice is beam configured but
      not scan configured; it is currently performing a configure scan operation
    * **CONFIGURING_READY**: the PST subdevice is scan configured;
      and is currently finishing the configure scan operation
    * **READY**: the PST subdevice is scan configured and waiting for a start scan
      request
    * **SCANNING**: the PST subdevice is scanning
    * **ABORTING**: the PST subdevice is aborting
    * **ABORTED**: the PST subdevice has aborted
    * **RESETTING**: the PST subdevice is resetting from an ABORTED or FAULT
      state back to IDLE
    * **FAULT**: the PST subdevice has encountered an observation fault.

    A diagram of the state machine is shown below. Reflexive transitions
    and transitions to FAULT obs state are omitted to simplify the
    diagram.

    .. uml:: obs_state_machine.puml
      :caption: Diagram of the PST subdevice state machine

    """

    def __init__(
        self: PstObsStateMachine,
        callback: Optional[Callable] = None,
        **extra_kwargs: Any,
    ) -> None:
        """
        Initialise the model.

        :param callback: A callback to be called when the state changes
        :type callback: callable
        :param extra_kwargs: Additional keywords arguments to pass to
            super class initialiser (useful for graphing)
        """
        self._callback = callback

        states = [
            "EMPTY",
            "RESOURCING_EMPTY",
            "RESOURCING_IDLE",
            "IDLE",
            "CONFIGURING_IDLE",
            "CONFIGURING_READY",
            "READY",
            "SCANNING",
            "ABORTING",
            "ABORTED",
            "RESETTING",
            "FAULT",
        ]
        transitions = [
            {
                "source": "*",
                "trigger": "component_obsfault",
                "dest": "FAULT",
            },
            {
                "source": "EMPTY",
                "trigger": "assign_invoked",
                "dest": "RESOURCING_EMPTY",
            },
            {
                "source": "EMPTY",
                "trigger": "release_invoked",
                "dest": "RESOURCING_EMPTY",
            },
            {
                "source": "IDLE",
                "trigger": "assign_invoked",
                "dest": "RESOURCING_IDLE",
            },
            {
                "source": "IDLE",
                "trigger": "release_invoked",
                "dest": "RESOURCING_IDLE",
            },
            {
                "source": "RESOURCING_EMPTY",
                "trigger": "component_resourced",
                "dest": "RESOURCING_IDLE",
            },
            {
                "source": "RESOURCING_IDLE",
                "trigger": "component_unresourced",
                "dest": "RESOURCING_EMPTY",
            },
            {
                "source": "RESOURCING_EMPTY",
                "trigger": "assign_completed",
                "dest": "EMPTY",
            },
            {
                "source": "RESOURCING_EMPTY",
                "trigger": "release_completed",
                "dest": "EMPTY",
            },
            {
                "source": "RESOURCING_IDLE",
                "trigger": "assign_completed",
                "dest": "IDLE",
            },
            {
                "source": "RESOURCING_IDLE",
                "trigger": "release_completed",
                "dest": "IDLE",
            },
            {
                "source": "IDLE",
                "trigger": "configure_invoked",
                "dest": "CONFIGURING_IDLE",
            },
            {
                "source": "CONFIGURING_IDLE",
                "trigger": "configure_completed",
                "dest": "IDLE",
            },
            {
                "source": "READY",
                "trigger": "configure_invoked",
                "dest": "CONFIGURING_READY",
            },
            {
                "source": "CONFIGURING_IDLE",
                "trigger": "component_configured",
                "dest": "CONFIGURING_READY",
            },
            {
                "source": "CONFIGURING_READY",
                "trigger": "configure_completed",
                "dest": "READY",
            },
            {
                "source": "READY",
                "trigger": "end_invoked",
                "dest": "READY",
            },
            {
                "source": "READY",
                "trigger": "component_unconfigured",
                "dest": "IDLE",
            },
            {
                "source": "READY",
                "trigger": "scan_invoked",
                "dest": "READY",
            },
            {
                "source": "READY",
                "trigger": "component_scanning",
                "dest": "SCANNING",
            },
            {
                "source": "SCANNING",
                "trigger": "end_scan_invoked",
                "dest": "SCANNING",
            },
            {
                "source": "SCANNING",
                "trigger": "component_not_scanning",
                "dest": "READY",
            },
            {
                "source": [
                    "IDLE",
                    "CONFIGURING_IDLE",
                    "CONFIGURING_READY",
                    "READY",
                    "SCANNING",
                    "RESETTING",
                ],
                "trigger": "abort_invoked",
                "dest": "ABORTING",
            },
            # Aborting implies trying to stop the monitored component
            # while it is doing something. Thus the monitored component
            # may send some events while in aborting state.
            {
                "source": "ABORTING",
                "trigger": "component_unconfigured",
                "dest": "ABORTING",
            },
            {
                "source": "ABORTING",
                "trigger": "component_configured",
                "dest": "ABORTING",
            },
            {
                "source": "ABORTING",
                "trigger": "component_not_scanning",
                "dest": "ABORTING",
            },
            {
                "source": "ABORTING",
                "trigger": "component_scanning",
                "dest": "ABORTING",
            },
            {
                "source": "ABORTING",
                "trigger": "abort_completed",
                "dest": "ABORTED",
            },
            {
                "source": ["ABORTED", "FAULT"],
                "trigger": "obsreset_invoked",
                "dest": "RESETTING",
            },
            {
                "source": "RESETTING",
                "trigger": "component_unconfigured",
                "dest": "RESETTING",
            },
            {
                "source": "RESETTING",
                "trigger": "component_unresourced",
                "dest": "RESETTING",
            },
            {
                "source": "RESETTING",
                "trigger": "obsreset_completed",
                "dest": "EMPTY",
            },
        ]

        super().__init__(
            states=states,
            initial="EMPTY",
            transitions=transitions,
            after_state_change=self._state_changed,
            **extra_kwargs,
        )
        self._state_changed()

    def _state_changed(self: PstObsStateMachine) -> None:
        """
        State machine callback that is called every time the obs_state changes.

        Responsible for ensuring that callbacks are called.
        """
        if self._callback is not None:
            self._callback(self.state)
