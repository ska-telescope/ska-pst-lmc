
Helm charts
===========

This page summarises the Helm chart parameters that can be used to customise
the PST.LMC deployment. The current default values can be found in the chart
``values.yaml`` files for 
`test_parent <https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/charts/test-parent/values.yaml>`_
and
`ska-pst-lmc <https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/charts/ska-pst-lmc/values.yaml>`_.

Release chart
-------------

The ``ska-pst-lmc`` chart deploys the latest release version of PST.LMC in simulation mode.
The current default Helm chart parameters can be viewed in the `values file`_.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``image.registry``
    - PST.LMC image registry
    - ``artefact.skao.int``
  * - ``image.image``
    - PST.LMC image name
    - ``ska-pst-lmc``
  * - ``strictValidation``
    - Enable strict validation of scan configuration schema
    - ``false``
  * - ``ska-tango-base.enabled``
    - Enable the ska-tango-base subchart
    - ``false``
  * - ``ska-tango-base.itango.enabled``
    - Enable the itango console in the ska-tango-base subchart
    - ``false``
  * - ``dsconfig.image.*``
    - Tango dsconfig container image settings
    - See `values file`_


Example of setting the ports used for communication between ska-pst-core and ska-pst-lmc

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

.. _values file: https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/charts/ska-pst-lmc/values.yaml
