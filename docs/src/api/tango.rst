.. _api_tango:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

PST.LMC TANGO API
=================

Here the external API via TANGO will be described, including

Properties
----------

Attributes that are configured in via Helm.

Commands
--------

=================== ============= =========== ======
Command             Argument type Return type Action
=================== ============= =========== ======
On                  None          None        Sets the device state to ON and the observing state to EMPTY.
Off                 None          None        Sets the device state to OFF.
Standby             None          None        Puts the device in STANDBY mode.
Configure           String (JSON) None        :ref:`Configures scan type for the following scans <pst_configure>`.
Deconfigure         None          None        Return to STANDBY mode.
Scan                String (JSON) None        :ref:`Begins a scan of the configured type <pst_scan>`.
EndScan             None          None        Ends the scan.
Abort               None          None        Aborts current activity.
ObsReset            None          None        Resets the subarray to the IDLE observing state.
Restart             None          None        Restarts the subarray in the EMPTY observing state.
=================== ============= =========== ======

.. _pst_configure:

Configure
^^^^^^^^^

The argument of the Configure command specifies the type of the following scans.

.. warning::

  PST.LMC will accept the Configure command only when in the IDLE state.

An example of the argument can be viewed at `Example CSP configuration for PST beam configuration
<https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>`_.

.. _pst_scan:

Scan
^^^^

The argument of the Scan command specifies the scan ID.

An example of the argument can be viewed at `Example JSON
<https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-scan.html>`_.

.. code-block:: json

  {
    "interface": "https://schema.skao.int/ska-pst-scan/0.4",
    "scan_id": 1
  }


Attributes
----------

================ ======= ========== ================================= ===========
Attribute        Type    Read/Write Values                            Description
================ ======= ========== ================================= ===========
version          String  Read       Semantic version                  Subarray device server version
---------------- ------- ---------- --------------------------------- -----------
healthState      Enum    Read       :ref:`health_state`      Subarray health state
---------------- ------- ---------- --------------------------------- -----------
adminMode        Enum    Read-write :ref:`admin_mode`        Subarray admin mode
---------------- ------- ---------- --------------------------------- -----------
obsState         Enum    Read       :ref:`obs_state`         Subarray observing state
---------------- ------- ---------- --------------------------------- -----------
scanType         String  Read                                         Scan type, or "null" if scan type is not configured
---------------- ------- ---------- --------------------------------- -----------
scanID           Integer Read                                         Scan ID, or 0 if not scanning
================ ======= ========== ================================= ===========

.. _health_state:

Health state values
^^^^^^^^^^^^^^^^^^^

============ ===========
healthState  Description
============ ===========
OK (0)       Subarray is functioning as expected
------------ -----------
DEGRADED (1) Subarray can only provide some of its functionality
------------ -----------
FAILED (2)   Subarray is unable to function
------------ -----------
UNKNOWN (3)  Subarray device is unable to determine the health of the subarray
============ ===========

.. _admin_mode:

Admin mode values
^^^^^^^^^^^^^^^^^

The admin mode represents the intent with which the subarray will be used. Some
admin mode values are not applicable to the subarray, but they are part of the
control system model so they are listed here for completeness.

=============== ===========
adminMode       Description
=============== ===========
ONLINE (0)      Subarray can be used for normal operations
--------------- -----------
OFFLINE (1)     Subarray should not be monitored or controlled by the control system
--------------- -----------
MAINTENANCE (2) Subarray can be used for maintenance purposes only
--------------- -----------
NOT_FITTED (3)  Subarray is not fitted and therefore cannot be used (not applicable)
--------------- -----------
RESERVED (4)    Subarray is reserved for redundancy purposes (not applicable)
=============== ===========

.. _obs_state:

Observing state values
^^^^^^^^^^^^^^^^^^^^^^

=============== ===========
obsState        Description
=============== ===========
EMPTY (0)       No resources are assigned to the subarray
--------------- -----------
RESOURCING (1)  Resources are being assigned or released
--------------- -----------
IDLE (2)        Resources are assigned to the subarray
--------------- -----------
CONFIGURING (3) Scan type is being configured
--------------- -----------
READY (4)       Scan type is configured and the subarray is ready to scan
--------------- -----------
SCANNING (5)    Scanning
--------------- -----------
ABORTING (6)    Current activity is being aborted
--------------- -----------
ABORTED (7)     Most recent activity has been aborted
--------------- -----------
RESETTING (8)   Resetting to IDLE observing state
--------------- -----------
FAULT (9)       A error has occurred in observing
--------------- -----------
RESTARTING (10) Restarting to return to EMPTY observing state
=============== ===========
