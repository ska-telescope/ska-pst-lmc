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
ObsReset            None          None        Resets PST to the IDLE observing state.
Restart             None          None        Restarts PST in the EMPTY observing state.
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

.. warning::

  PST.LMC will accept the Scan command only when in the READY state.

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
version          String  Read       Semantic version                  PST device server version
---------------- ------- ---------- --------------------------------- -----------
healthState      Enum    Read       :ref:`health_state`               PST health state
---------------- ------- ---------- --------------------------------- -----------
adminMode        Enum    Read-write :ref:`admin_mode`                 PST admin mode
---------------- ------- ---------- --------------------------------- -----------
obsState         Enum    Read       :ref:`obs_state`                  PST observing state
---------------- ------- ---------- --------------------------------- -----------
scanType         String  Read                                         Scan type, or "null" if scan type is not configured
---------------- ------- ---------- --------------------------------- -----------
scanID           Integer Read                                         Scan ID, or 0 if not scanning
---------------- ------- ---------- --------------------------------- -----------
config           String  Read                                         Current channel block configuration
---------------- ------- ---------- --------------------------------- -----------
expectedRate     Float   Read                                         Expected incoming data rate in bytes per second
---------------- ------- ---------- --------------------------------- -----------
receivedRate     Float   Read                                         Current received data rate in bytes per second
---------------- ------- ---------- --------------------------------- -----------
receivedData     Integer Read                                         Current received data in bytes
---------------- ------- ---------- --------------------------------- -----------
droppedRate      Float   Read                                         Current dropped data rate in bytes per second
---------------- ------- ---------- --------------------------------- -----------
droppedData      Integer Read                                         Current dropped data in bytes
---------------- ------- ---------- --------------------------------- -----------
writtenRate      Float   Read                                         Current written data rate in bytes per second
---------------- ------- ---------- --------------------------------- -----------
writtenData      Integer Read                                         Current written data in bytes
---------------- ------- ---------- --------------------------------- -----------
diskAvailable    Integer Read                                         Current available recording space in bytes
---------------- ------- ---------- --------------------------------- -----------
timeAvailable    Float   Read                                         Current available recording time in seconds
---------------- ------- ---------- --------------------------------- -----------
bufferUsed       Float   Read                                         Current fractional utilisation of ring buffer
================ ======= ========== ================================= ===========

.. _health_state:

Health state values
^^^^^^^^^^^^^^^^^^^

============ ===========
healthState  Description
============ ===========
OK (0)       PST is functioning as expected
------------ -----------
DEGRADED (1) PST can only provide some of its functionality
------------ -----------
FAILED (2)   PST is unable to function
------------ -----------
UNKNOWN (3)  PST.LMC is unable to determine the health of the sub-element
============ ===========

.. _admin_mode:

Admin mode values
^^^^^^^^^^^^^^^^^

The admin mode represents the intent with which the PST will be used. Some
admin mode values are not applicable to PST, but they are part of the
control system model so they are listed here for completeness.

=============== ===========
adminMode       Description
=============== ===========
ONLINE (0)      PST can be used for normal operations
--------------- -----------
OFFLINE (1)     PST should not be monitored or controlled by the control system
--------------- -----------
MAINTENANCE (2) PST can be used for maintenance purposes only
--------------- -----------
NOT_FITTED (3)  PST is not fitted and therefore cannot be used (not applicable)
--------------- -----------
RESERVED (4)    PST is reserved for redundancy purposes (not applicable)
=============== ===========

.. _obs_state:

Observing state values
^^^^^^^^^^^^^^^^^^^^^^

=============== ===========
obsState        Description
=============== ===========
EMPTY (0)       No resources are assigned to PST
--------------- -----------
RESOURCING (1)  Resources are being assigned or released
--------------- -----------
IDLE (2)        Resources are assigned to PST
--------------- -----------
CONFIGURING (3) Scan type is being configured
--------------- -----------
READY (4)       Scan type is configured and PST is ready to scan
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
