==============================================
Shared Memory Ring Buffer MGMT Tango Component
==============================================

The Shared Memory Ring Buffer (SMRB.MGMT) Tango Component
is used to manage the SMRB.CORE process.

This is component is made up of a Tango device, a component
manager, as well as including a simulator and a gRPC
Process API, which used by the component to talk with the
SMRB process via gRPC + Protobuf.

For more information about SMRB.CORE check:

  * `SMRB.CORE code repository <https://gitlab.com/ska-telescope/pst/ska-pst-smrb>`_
  * `SMRB.CORE online documentation <https://developer.skao.int/projects/ska-pst-smrb>`_

.. toctree::
  :caption: API
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>
  Model<model>
  Process API<process_api>
  Simulator<simulator>
