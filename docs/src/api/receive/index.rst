=======================
Receive TANGO Component
=======================

The Receive (RECV) TANGO Component is used to manage the
RECV sub-element for PST.LMC.

This is component is made up of a TANGO device, a component
manager, as well as including a simulator and an API.

The API is to be used by the component to talk with the
sub-element process (i.e. via socket, gRPC, etc.). For now
the component uses the Simulator internally.

.. toctree::
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>
  Model<model>
  Process API<process_api>
  Simulator<simulator>
