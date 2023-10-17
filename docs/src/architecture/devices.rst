.. _architecture_tango:

TANGO Devices
=============

Five PST TANGO devices (BEAM, SMRB, RECV, DSP, and STAT.*) are deployed in a single TANGO Device server.
For AA0.5, each deployment of PST supports a single beam; multiple device servers could be deployed to support multiple beams.

Full PST control and monitoring is accessed via the BEAM device.
Following the SKA TANGO device naming convention, access to the Low PST Beam 1 would use the TANGO FQDN of ``low-pst/beam/01``.

All PST TANGO devices extend from the SKA TANGO base
`CSP Subelement Obs Device <https://developer.skao.int/projects/ska-csp-lmc-base/en/latest/api/obs/obs_device.html>`_
(``ska_csp_lmc_base.CspSubElementObsDevice``)
which in turn extends from the
`Obs Device <https://developer.skao.int/projects/ska-tango-base/en/latest/api/obs/obs_device.html>`_
(``ska_tango_base.obs.ObsDevice``) and
`Base Device <https://developer.skao.int/projects/ska-tango-base/en/latest/api/base/base_device.html>`_
(``ska_tango_base.base.SKABaseDevice``).


BEAM
----

This logical device implements the single point of contact for monitor and control between PST and
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

* AA0.5 voltage recorder (DSP.DISK) writes raw data from the beam former to files on disk
* AA1.0 search mode
* AA2.0 timing mode

STAT
----

This device controls and monitors the STAT process that reads incoming data from the ring buffer
in shared memory and processes it according to configured publishers.
