.. _architecture_tango:

TANGO Devices
=============

BEAM
----

This logical device implements the single point of contact between PST.LMC and
external systems, such as CSP.LMC or an engineering interface.
It manages all of the other PST component devices (in AA0.5, these are SMRB, RECV, and DSP.DISK). 

SMRB
----

This device controls and monitors the SMRB process that manages the ring buffers in shared memory.

RECV
----

This device controls and monitors the RECV process that is responsible for capturing UDP packet
streams from the Beam Former and writing the data to ring buffers in shared memory.

DSP
---

This device controls and monitors the DSP process that reads incoming data from the ring buffer
in shared memory and processes it according to the configured mode of operation.  New modes of operation
will be made available with each array assembly:

* AA0.5 voltage recorder (DSP.DISK)
* AA1.0 search mode
* AA2.0 timing mode

