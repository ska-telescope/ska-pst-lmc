.. _operation_itango:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Using itango
============

By default, the ``ska-pst`` chart does not deploy the iTango shell pod from the
``ska-tango-base`` chart. To enable it, you can upgrade the release with:

.. code-block:: console

    $ helm upgrade test ska/ska-pst --set ska-tango-base.itango.enabled=true

This command will need to be modified for non-default namespaces:

.. code-block:: console

    $ helm upgrade test ska/ska-pst -n <namespace> --set helmdeploy.namespace=<pst-namespace>,ska-tango-base.itango.enabled=true

Then you can start an iTango session with:

.. code-block:: console

    $ kubectl exec -it ska-tango-base-itango-console -n <namespace> -- itango3

You should be able to list the Tango devices:

:red:`Include an example from PST.LMC`

.. code-block:: python

    In [1]: lsdev
    Device                                   Alias                     Server                    Class
    ---------------------------------------- ------------------------- ------------------------- --------------------
    test-pst/control/0                                                 pstController/0           pstController
    test-pst/subarray/01                                               pstSubarray/01            pstSubarray
    sys/access_control/1                                               TangoAccessControl/1      TangoAccessControl
    sys/database/2                                                     DataBaseds/2              DataBase
    sys/rest/0                                                         TangoRestServer/rest      TangoRestServer
    sys/tg_test/1                                                      TangoTest/test            TangoTest

This interface allows direct interaction with the devices, such as querying and
changing attributes and issuing Tango commands to control pst processing. 

:red:`Include an example from PST.LMC`

.. code-block:: python

    In [2]: d = DeviceProxy('test-pst/beam/01')

    In [3]: d.state()
    Out[3]: tango._tango.DevState.OFF

    In [4]: d.On()

    In [5]: d.state()
    Out[5]: tango._tango.DevState.ON

    In [6]: d.obsState
    Out[6]: <obsState.EMPTY: 0>

The arguments of the ``configure`` and ``scan`` commands include strings
containing data in JSON format. The configuration string sets the mode of 
operation and provides the values of various required attributes, and the
scan string simply sets the scan ID.

The format of the JSON strings are described by schema which are
versioned to support evolution of the interfaces. A specific scheme is 
specified with the ``interface`` keyword in the JSON string:

.. code-block:: json

  {
    "interface": "https://schema.skao.int/ska-csp-<command>/<version>",
    "...": "..."
  }

where ``<command>`` identifies the command:

- ``configure`` - Configure command
- ``scan`` - Scan command

and ``<version>`` is the version of the scheme.

The JSON string can be validated against the scheme using the `telescope model
library <https://developer.skao.int/projects/ska-telmodel/en/latest/>`_. Its
documentation describes the versions of the schema. The PST.BEAM device
implements version :red:`2.3` of the CSP schemas, which is used in the example below.

`Example CSP configuration for PST beam configuration
<https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>`_

:red:`Include links to more example JSON strings that can be cut and pasted into itango?`

In the following example, it is assumed that the copied JSON configuration is saved as
a python string named ``test_configuration``.

.. code-block:: python

    In [9]: d.obsState
    Out[9]: <obsState.IDLE: 0>

    In [10]: d.Configure(test_configuration)

    In [11]: d.obsState
    Out[11]: <obsState.READY: 2>

    In [12]: d.Scan('{"interface": "https://schema.skao.int/ska-csp-scan/2.3", "scan_id": 1}')

    In [13]: d.obsState
    Out[13]: <obsState.SCANNING: 3>

    In [14]: d.EndScan()

    In [15]: d.obsState
    Out[15]: <obsState.READY: 2>

    In [16]: d.End()

    In [17]: d.obsState
    Out[17]: <obsState.IDLE: 0>

    In [20]: d.Off()

    In [21]: d.state()
    Out[21]: tango._tango.DevState.OFF
