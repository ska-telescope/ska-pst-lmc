=========================================
Shared Memory Ring Buffer TANGO Component
=========================================

The Shared Memory Ring Buffer (SMRB) TANGO Component
is used to manage the SMRB sub-element for PST.LMC.

This is component is made up of a TANGO device, a component
manager, as well as including a simulator and an API.

The API is to be used by the component to talk with the
sub-element process (i.e. via socket, gRPC, etc.). For now
the component uses the Simulator internally.

.. toctree::

  Component Manager<component_manager>
  Device<device>
  Model<model>
  Process API<process_api>
  Simulator<simulator>

.. automodule:: ska_pst_lmc.smrb
