=======================
Beam TANGO Component
=======================

The Beam (BEAM) TANGO Component is a logical TANGO
component that is used to manage the sub-element
devices and processes of the PST.LMC.

This component current proxies the commands to RECV, SMRB,
and DSP devices. In the future it will also support the SEND
devices.

Unlike the RECV and SMRB devices, this doesn't use
a simulator or an API class as it orchestrates the other
devices.

.. toctree::
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>

