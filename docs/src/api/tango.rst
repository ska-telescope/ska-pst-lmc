.. _api_tango:

PST.LMC Tango API
=================

This page describes the properties, commands, and attributes exposed by
the Tango interface of each PST.BEAM.

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
ConfigureScan       String (JSON) None        :ref:`Configures all following scans <pst_configure>`.
GoToIdle            None          None        Return to IDLE mode.
Scan                String (ID)   None        Begins a scan with the specified scan identifier.
EndScan             None          None        Ends the scan.
Abort               None          None        Aborts current activity.
ObsReset            None          None        Resets PST to the IDLE observing state.
=================== ============= =========== ======

.. _pst_configure:

Configure
^^^^^^^^^

The argument of the Configure command is a JSON string that specifies the type and configuration of the following scans.

`Example CSP configuration for PST beam configuration
<https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>`_.

Attributes
----------

In addition to the attributes made visible in the Tango interface by  
`SkaObsDevice <https://developer.skao.int/projects/lmc-base-classes/en/latest/SKAObsDevice.html>`_
and
`SKABaseDevice <https://developer.skao.int/projects/lmc-base-classes/en/latest/SKABaseDevice.html>`_,
each PST.BEAM exposes the following read-only attributes for monitoring.

========================== ======= ===========
Attribute                  Type    Description
========================== ======= ===========
channelBlockConfiguration  String  Current channel block configuration
-------------------------- ------- -----------
expectedDataRecordRate     Float   Expected incoming data rate in bytes per second
-------------------------- ------- -----------
dataReceiveRate            Float   Current received data rate in bytes per second
-------------------------- ------- -----------
dataReceived               Integer Current received data in bytes
-------------------------- ------- -----------
dataDropRate               Float   Current dropped data rate in bytes per second
-------------------------- ------- -----------
dataDropped                Integer Current dropped data in bytes
-------------------------- ------- -----------
dataRecordRate             Float   Current written data rate in bytes per second
-------------------------- ------- -----------
dataRecorded               Integer Current written data in bytes
-------------------------- ------- -----------
availableDiskSpace         Integer Current available recording space in bytes
-------------------------- ------- -----------
availableRecordingTime     Float   Current available recording time in seconds
-------------------------- ------- -----------
ringBufferUtilisation      Float   Current fractional utilisation of ring buffer
========================== ======= ===========

As a `CSP Sub-element ObsDevice <https://developer.skao.int/projects/lmc-base-classes/en/latest/CspSubElementObsDevice.html>`_,
each PST.BEAM also exposes the following read-only attributes.

========================== ======= ===========
Attribute                  Type    Description
========================== ======= ===========
scanID                     String  Scan identifier
-------------------------- ------- -----------
configurationID            String  Configuration identifier
-------------------------- ------- -----------
deviceID                   String  Device identifier
-------------------------- ------- -----------
lastScanConfiguration      String  JSON string of the last Configure command
-------------------------- ------- -----------
sdpDestinationAddresses    String  SDP addresses to receive output products
-------------------------- ------- -----------
sdpLinkCapacity            Float   The SDP link capavity in GB/s
-------------------------- ------- -----------
sdpLinkActive              Boolean Flag reporting if the SDP link is active
-------------------------- ------- -----------
healthFailureMessage       String  Message providing info about device health failure
========================== ======= ===========
