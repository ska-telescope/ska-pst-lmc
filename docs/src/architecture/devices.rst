.. raw:: html
    
    <style> .tt {font-family:'Courier New'} </style>

.. role:: tt

TANGO Devices
=============

BEAM Device
-----------

This device implements the single point of contact between PST.LMC and
external systems, such as CSP.LMC or an engineering interface.
It is a purely logical device for managing all of the PST component
devices (in AA0.5, these are RECV, SMRB, and DSP.DISK). 
The BEAM device uses references to a `PstDeviceProxy` which
is a wrapper around the `tango.DeviceProxy` class. 
This allows for not having to import TANGO classes within component classes.

The component manager proxies commands to the remote devices that are 
configured based on the TANGO device's attributes of 
`RecvFQDN`, `SmrbFQDN`, `DspFQDN`.

Base classes
------------

The `ska_pst_lmc.component` module defines common base classes for 
PST.LMC TANGO device components. For now, the only class
in this module is the `PstComponentManager`, though a base PST Process API 
may also be added here.

Common reusable code (i.e. code that can be used by a completely separate project) is to be added to the `ska_pst_lmc.util` module and not the component submodule.

RECV Device
-----------

This device is used for managing and monitoring the RECV process within the PST.LMC sub-system. This is the base example for
which the other devices are to be modelled upon. It includes the use of:

* SKASubarray TANGO Device (found in the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base))
* A Component Manager extending from `PstComponentManager`
* A process API
* A RECV Model module
* A simulator

While the Process API is similar to the Component Manager, it's goal is different. The Component Manager uses the API which
will ultimately connect to the RECV process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the component manager.

SMRB Device
-----------

This device is used for managing and monitoring the Shared Memory Ring Buffer (SMRB) process within the PST.LMC sub-system.
It includes the use of:

* SKASubarray TANGO Device (found in the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base))
* A Component Manager extending from `PstComponentManager`
* A process API
* A SMRB Model module
* A simulator

While the Process API is similar to the Component Manager, it's goal is different. The Component Manager uses the API which
will ultimately connect to the SMRB process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the component manager.

DSP Device
----------

This device is used for managing and monitoring the Digital Signal Processing (DSP) process within the PST.LMC sub-system.
It includes the use of:

* SKASubarray TANGO Device (found in the [ska-tango-base](https://gitlab.com/ska-telescope/ska-tango-base))
* A Component Manager extending from `PstComponentManager`
* A process API
* A SMRB Model module
* A simulator

While the Process API is similar to the Component Manager, it's goal is different. The Component Manager uses the API which
will ultimately connect to the DSP process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the component manager.

