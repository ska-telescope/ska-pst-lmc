==============================================
Shared Memory Ring Buffer MGMT TANGO Component
==============================================

The Shared Memory Ring Buffer (SMRB.MGMT) TANGO Component
is used to manage the SMRB.CORE process.

This component is made up of a TANGO device, a component
manager, as well as including a simulator and a gRPC
Process API, which are used by the component to talk with the
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
