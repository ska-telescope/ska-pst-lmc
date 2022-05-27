=======================
Beam TANGO Component
=======================

The Beam (BEAM) TANGO Component is a logical TANGO
component that is used to manage the sub-element
devices and processes of the PST.LMC.

This component current proxies the commands to RECV
and SMRB devices, but in the future will also manage
the DSP and SEND devices.

Unlike the RECV and SMRB devices, this doesn't use
a simulator or API class. The simulation happens at
the software devices.

.. automodule:: ska_pst_lmc.beam

.. toctree::

  Component Manager<component_manager>
  Device<device>
