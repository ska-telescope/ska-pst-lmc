.. _api_tango:

PST.LMC TANGO API
=================

This page describes the properties, commands, and attributes exposed by
the TANGO interface of each PST.BEAM.

Properties
----------

The following properties are common to all PST TANGO devices.

========================== ======= ======= ===========
Property                   Type    Default Description
========================== ======= ======= ===========
facility                   String  Low     Low or Mid (where PST is deployed)
subsystem_id               String  pst-low pst-low or pst-mid (where PST is deployed)
========================== ======= ======= ===========

The following properties are common to SMRB, RECV, DSP, and STAT TANGO devices.

========================== ======= ======= ===========
Property                   Type    Default Description
========================== ======= ======= ===========
process_api_endpoint       String          URL for gRPC service of the core application that it manages
monitor_polling_rate       Integer 5000    Polling period in milliseconds for querying core application attributes
========================== ======= ======= ===========

The following properties are specific to the BEAM TANGO device.

========================== ======= ======= ===========
Property                   Type    Default Description
========================== ======= ======= ===========
SmrbFQDN                   String          FQDN for SMRB.MGMT TANGO Device
RecvFQDN                   String          FQDN for RECV.MGMT TANGO Device
DspFQDN                    String          FQDN for DSP.MGMT TANGO Device
StatFQDN                   String          FQDN for DSP.MGMT TANGO Device
SendFQDN                   String          FQDN for SEND.MGMT TANGO Device (not currently used)
========================== ======= ======= ===========

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

ConfigureScan
^^^^^^^^^^^^^

The argument of the ConfigureScan command is a JSON string that specifies the type and configuration of the following scans.

Currently, the PST supports `CSP config 2.4 <https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>`_.

`Example CSP configuration for PST beam configuration
<https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>`_.

Attributes
----------

In addition to the attributes made visible in the TANGO interface by
`SkaObsDevice <https://developer.skao.int/projects/lmc-base-classes/en/latest/SKAObsDevice.html>`_
and
`SKABaseDevice <https://developer.skao.int/projects/lmc-base-classes/en/latest/SKABaseDevice.html>`_,
each PST.BEAM exposes the following read-only attributes for monitoring.

========================== ======= ===========
Attribute                  Type    Description
========================== ======= ===========
channelBlockConfiguration  String  Current channel block configuration
expectedDataRecordRate     Float   Expected incoming data rate in bytes per second
dataReceiveRate            Float   Current received data rate in bytes per second
dataReceived               Integer Current received data in bytes
dataDropRate               Float   Current dropped data rate in bytes per second
dataDropped                Integer Current dropped data in bytes
dataRecordRate             Float   Current written data rate in bytes per second
dataRecorded               Integer Current written data in bytes
availableDiskSpace         Integer Current available recording space in bytes
availableRecordingTime     Float   Current available recording time in seconds
ringBufferUtilisation      Float   Current fractional utilisation of ring buffer
========================== ======= ===========

The following attributes are only available from the STAT.MGMT device

==================================== ======== ===========
Attribute                            Type     Description
==================================== ======== ===========
realPolAMeanFreqAvg                  Float    The mean of the real data for pol A, averaged over all channels.
realPolAVarianceFreqAvg              Float    The variance of the real data for pol A, averaged over all channels.
realPolANumClippedSamples            Integer  The number of clipped samples of the real data for pol A.
imagPolAMeanFreqAvg                  Float    The mean of the imaginary data for pol A, averaged over all channels.
imagPolAVarianceFreqAvg              Float    The variance of the imaginary data for pol A, averaged over all channels.
imagPolANumClippedSamples            Integer  The number of clipped samples of the imaginary data for pol A.
realPolAMeanFreqAvgRfiExcised        Float    The mean of the real data for pol A, averaged over channels without RFI.
realPolAVarianceFreqAvgRfiExcised    Float    The variance of the real data for pol A, averaged over channels without RFI.
realPolANumClippedSamplesRfiExcised  Integer  The number of clipped samples of the real data for pol A in channels without RFI.
imagPolAMeanFreqAvgRfiExcised        Float    The mean of the imaginary data for pol A, averaged over channels without RFI.
imagPolAVarianceFreqAvgRfiExcised    Float    The variance of the imaginary data for pol A, averaged over channels without RFI.
imagPolANumClippedSamplesRfiExcised  Integer  The number of clipped samples of the imaginary data for pol A in channels without RFI.
realPolBMeanFreqAvg                  Float    The mean of the real data for pol B, averaged over all channels.
realPolBVarianceFreqAvg              Float    The variance of the real data for pol B, averaged over all channels.
realPolBNumClippedSamples            Integer  The number of clipped samples of the real data for pol B.
imagPolBMeanFreqAvg                  Float    The mean of the imaginary data for pol B, averaged over all channels.
imagPolBVarianceFreqAvg              Float    The variance of the imaginary data for pol B, averaged over all channels.
imagPolBNumClippedSamples            Integer  The number of clipped samples of the imaginary data for pol B.
realPolBMeanFreqAvgRfiExcised        Float    The mean of the real data for pol B, averaged over channels without RFI.
realPolBVarianceFreqAvgRfiExcised    Float    The variance of the real data for pol B, averaged over channels without RFI.
realPolBNumClippedSamplesRfiExcised  Integer  The number of clipped samples of the real data for pol B in channels without RFI.
imagPolBMeanFreqAvgRfiExcised        Float    The mean of the imaginary data for pol B, averaged over channels without RFI.
imagPolBVarianceFreqAvgRfiExcised    Float    The variance of the imaginary data for pol B, averaged over channels without RFI.
imagPolBNumClippedSamplesRfiExcised  Integer  The number of clipped samples of the imaginary data for pol B in channels without RFI.
==================================== ======== ===========

From CspSubElementObsDevice
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As a `CSP Sub-element Obs Device <https://developer.skao.int/projects/ska-tango-base/en/latest/api/csp/obs/obs_device.html>`_,
each PST.BEAM also exposes the following read-only attributes.

========================== ======= ===========
Attribute                  Type    Description
========================== ======= ===========
scanID                     String  Scan identifier
configurationID            String  Configuration identifier
deviceID                   String  Device identifier
lastScanConfiguration      String  JSON string of the last Configure command
sdpDestinationAddresses    String  SDP addresses to receive output products
sdpLinkCapacity            Float   The SDP link capavity in GB/s
sdpLinkActive              Boolean Flag reporting if the SDP link is active
healthFailureMessage       String  Message providing info about device health failure
========================== ======= ===========

From SKAObsDevice
^^^^^^^^^^^^^^^^^

As an `SKA Obs Device <https://developer.skao.int/projects/ska-tango-base/en/latest/api/obs/obs_device.html>`_,
each PST.BEAM also exposes the following read-only attributes.

========================== ======== ===========
Attribute                  Type     Description
========================== ======== ===========
obsState                   ObsState Observation State of the device
obsMode                    ObsMode  Observation Mode of the device
configurationProgress      Integer  Percentage configuration completion of the device
configurationDelayExpected Integer  Expected Configuration Delay in seconds
========================== ======== ===========

From SKABaseDevice
^^^^^^^^^^^^^^^^^^

Please see the `SKABaseDevice documentation <https://developer.skao.int/projects/ska-tango-base/en/latest/api/base/base_device.html>`_.


