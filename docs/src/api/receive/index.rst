============================
Receive MGMT TANGO Component
============================

The Receive (RECV.MGMT) TANGO Component is used to manage the
RECV.CORE process.

This component is made up of a TANGO device, a component
manager, as well as including a simulator and a gRPC
Process API, which are used by the component to talk with the
RECV process via gRPC + Protobuf.

For more information about RECV.CORE check:

  * `RECV.CORE code repository <https://gitlab.com/ska-telescope/pst/ska-pst-recv>`_
  * `RECV.CORE online documentation <https://developer.skao.int/projects/ska-pst-recv>`_

.. toctree::
  :caption: API
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>
  Model<model>
  Process API<process_api>
  Simulator<simulator>
