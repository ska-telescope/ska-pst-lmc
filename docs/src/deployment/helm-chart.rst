
Helm charts
===========

This page summarises the Helm chart parameters that can be used to customise
the PST.LMC Release and Development deployments. 

Release chart
-------------

The ``ska-pst-lmc`` chart deploys the latest release of PST.LMC from the ``artefact.skao.int`` registry.
By default, PST.LMC is deployed in simulation mode.
The current default Helm chart parameters can be viewed in the ``ska-pst-lmc`` `values file <https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/charts/ska-pst-lmc/values.yaml>`_.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``global.ports``
    - Port configuration for component devices
    - ``smrb``, ``recv``, and ``dsp``
  * - ``global.ports.smrb``
    - Port configuration for SMRB component device
    - ``smrb-mgmt``
  * - ``global.ports.smrb.smrb-mgmt``
    - Port configuration for SMRB component manager
    - ``port``, ``protocol``
  * - ``global.ports.smrb.smrb-mgmt.port``
    - Port used by SMRB component manager
    - 8080
  * - ``global.ports.recv.recv-mgmt.port``
    - Port used by RECV component manager
    - 8080
  * - ``global.ports.dsp.dsp-mgmt.port``
    - Port used by DSP component manager
    - 8080
  * - ``beam.simulationMode``
    - Run Beam logical device in simulation mode
    - 1
  * - ``smrb.simulationMode``
    - Run SMRB component device in simulation mode
    - 1
  * - ``recv.simulationMode``
    - Run RECV component device in simulation mode
    - 1
  * - ``dsp.simulationMode``
    - Run DSP component device in simulation mode
    - 1

Example of changing the ports used for communication between the PST Beam logical device and component device managers.

.. code-block:: yaml

    global:
        ports:
            recv:
                recv-mgmt:
                    port:       28080
            smrb:
                smrb-mgmt:
                    port:       28081
            dsp:
                dsp-mgmt:
                    port:       28082


Example of running in normal mode (not simulation mode).

.. code-block:: yaml

    beam:
      simulationMode: 1
    
    smrb:
      simulationMode: 1
    
    recv:
      simulationMode: 1
    
    dsp:
      simulationMode: 1

Development chart
-----------------

The ``test-parent`` chart deploys the latest build of PST.LMC from ``registry.gitlab.com/ska-telescope/pst/ska-pst-lmc``.
The current default Helm chart parameters can be viewed in the 
``values.yaml`` file for
`test_parent <https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/charts/test-parent/values.yaml>`_.

