==============================================
Statistics MGMT TANGO Component
==============================================

The Statistics (STAT.MGMT) TANGO
Component is used to manage the STAT.CORE process that is
used in the signal processing chain to calculate real time
statistics of a scan.

This component is made up of a TANGO device, a component
manager, as well as including a simulator and a gRPC
Process API, which are used by the component to talk with the
STAT process via gRPC + Protobuf.

For more information about STAT.CORE check:

  * `STAT.CORE code repository <https://gitlab.com/ska-telescope/pst/ska-pst-stat>`_
  * `STAT.CORE online documentation <https://developer.skao.int/projects/ska-pst-stat>`_

.. toctree::
  :caption: API
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>
  Model<model>
  Process API<process_api>
  Simulator<simulator>
