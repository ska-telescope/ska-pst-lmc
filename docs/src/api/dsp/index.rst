==============================================
Digital Signal Processing MGMT TANGO Component
==============================================

The Digital Signal Processing (DSP.MGMT) TANGO
Component is used to manage the DSP.CORE process.

This is component is made up of a TANGO device, a component
manager, as well as including a simulator and a gRPC
Process API, which used by the component to talk with the
DSP process via gRPC + Protobuf.

For more information about DSP.CORE check:

  * `DSP.CORE code repository <https://gitlab.com/ska-telescope/pst/ska-pst-dsp>`_
  * `DSP.CORE online documentation <https://developer.skao.int/projects/ska-pst-dsp>`_

.. toctree::
  :caption: API
  :maxdepth: 1

  Component Manager<component_manager>
  Device<device>
  Model<model>
  Process API<process_api>
  Simulator<simulator>
