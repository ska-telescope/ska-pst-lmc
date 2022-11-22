
Helm chart
==========

This is a summary of the Helm chart parameters that can be used to customise
the PST.LMC deployment. The current default values can be found in the chart's
`values file`_.

Helm deployer
-------------

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``helmdeploy.image``
    - Helm deployer container image
    - ``artefact.skao.int/ska-pst-helmdeploy``
  * - ``helmdeploy.version``
    - Helm deployer container version
    - See `values file`_
  * - ``helmdeploy.imagePullPolicy``
    - Helm deployer container image pull policy
    - ``IfNotPresent``
  * - ``helmdeploy.namespace``
    - Namespace for pst dynamic deployments
    - ``pst``
  * - ``helmdeploy.releasePrefix``
    - Prefix for Helm release names
    - ``""``
  * - ``helmdeploy.chartPrefix``
    - Prefix for Helm chart names
    - ``""``
  * - ``helmdeploy.chartRepo.url``
    - Chart repository URL
    - ``https://gitlab.com/ska-telescope/pst/ska-pst-helmdeploy-charts/-/raw/master/chart-repo/``
  * - ``helmdeploy.chartRepo.refresh``
    - Chart repository refresh interval (in seconds)
    - ``0``


LMC (Tango devices)
-------------------

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``lmc.enabled``
    - Enable the LMC. If set to ``false``, the PST.LMC will run in headless mode
    - ``true``
  * - ``lmc.image``
    - LMC container image
    - ``artefact.skao.int/ska-pst-lmc``
  * - ``lmc.version``
    - LMC container version
    - See `values file`_
  * - ``lmc.imagePullPolicy``
    - LMC container image pull policy
    - ``IfNotPresent``
  * - ``lmc.nsubarray``
    - Number of subarrays to deploy
    - ``1``
  * - ``lmc.prefix``
    - Telescope prefix for Tango device names (e.g. ``low`` or ``mid``)
    - ``test``
  * - ``lmc.newDeviceNames``
    - Use new-style Tango device names defined in `ADR-9`_
    - ``true``
  * - ``lmc.allCommandsHaveArgument``
    - Enable all Tango device commands to receive a transaction ID
    - ``false``
  * - ``lmc.strictValidation``
    - Enable strict validation of subarray command schemas
    - ``false``


Tango infrastructure
--------------------

Parameters for the ska-tango-base subchart and Tango dsconfig. The
ska-tango-base subchart must be enabled to support the Tango devices when
running the PST.LMC stand-alone.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``ska-tango-base.enabled``
    - Enable the ska-tango-base subchart
    - ``true``
  * - ``ska-tango-base.itango.enabled``
    - Enable the itango console in the ska-tango-base subchart
    - ``false``
  * - ``dsconfig.image.*``
    - Tango dsconfig container image settings
    - See `values file`_


Proxy settings
--------------

Proxy settings are applied to the components that retrieve configuration data
via HTTPS: the script definitions and the Helm charts.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``proxy.server``
    - Address of proxy server
    - Not set
  * - ``proxy.noproxy``
    - List of addresses or subnets for which the proxy should not be used
    - Not set

Example of proxy settings in a values file:

.. code-block:: yaml

  proxy:
    server: http://proxy.mydomain
    noproxy:
    - 192.168.0.1
    - 192.168.0.2


.. _values file: https://gitlab.com/ska-telescope/pst/ska-pst-integration/-/blob/master/charts/ska-pst/values.yaml
.. _etcd: https://etcd.io
.. _scripts repository: https://gitlab.com/ska-telescope/pst/ska-pst-script
.. _ADR-9: https://confluence.skatelescope.org/display/SWSI/ADR-9+Update+naming+conventions+for+TANGO+Devices+and+Servers