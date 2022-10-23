==========================
BEAM.MGMT TANGO Component
==========================

The Beam (BEAM) MGMT TANGO Component is a logical TANGO
component that is used to manage the separate TANGO
components that manage the separate processes that make
up the PST.LMC system.

This component orchestrates the LMC commands, such as
Configure or Scan, to the RECV.MGMT, SMRB.MGMT, and
DSP.MGMT components. As such this component doesn't use
as Simulator or a gRPC Process API.

.. toctree::
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>

