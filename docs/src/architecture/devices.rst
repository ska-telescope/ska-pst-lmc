.. _architecture_tango:

TANGO Devices
=============

BEAM Device
-----------

This device implements the single point of contact between PST.LMC and
external systems, such as CSP.LMC or an engineering interface.
It is a purely logical device for managing all of the PST component
devices (in AA0.5, these are RECV, SMRB, and DSP.DISK). 
The BEAM device uses references to a ``PstDeviceProxy`` which
is a wrapper around the ``tango.DeviceProxy`` class. 
This allows for not having to import TANGO classes within component classes.

The component manager proxies commands to the remote devices that are 
configured based on the TANGO device's attributes of 
``RecvFQDN``, ``SmrbFQDN``, ``DspFQDN``.

Base classes
------------

The ``ska_pst_lmc.component`` module defines common base classes for 
PST.LMC TANGO device components. The primary base classes
in this module are 

- ``PstComponentManager``, which extends the `CspObsComponentManager <https://developer.skao.int/projects/ska-tango-base/en/latest/api/csp/obs/component_manager.html>`_; and
- ``PstProcessApi``, an abstract class that defines the API of PST.LMC processes like RECV, SMRB, etc.
- ``PstBaseDevice``, the base class for all TANGO devices in PST.LMC, extends `CspSubElementObsDevice <https://developer.skao.int/projects/ska-tango-base/en/latest/api/csp/obs/obs_device.html>`_

While ``PstProcessApi`` is similar to the ``PstComponentManager``, it's goal is different. The Component Manager uses the API which
will ultimately connect to the actual process or a stubbed/simulator process. It is meant to deal with the communication with
the external process and also not worry about the state model, which is a part of the Component Manager.

Common reusable code (i.e. code that can be used by a completely separate project) is to be added to the ``ska_pst_lmc.util`` module and not the component submodule.

Component Devices
-----------------

Component devices that extend ``PstBaseDevice`` are used for managing and monitoring the 

- UDP Packet Capture (RECV) process;
- Shared Memory Ring Buffer (SMRB) process; and
- Digital Signal Processing (DSP) process

Each device uses

* a Component Manager extending from ``PstComponentManager``
* a process API extending from ``PstProcessApi``
* a Component Model module; and
* a simulator.
