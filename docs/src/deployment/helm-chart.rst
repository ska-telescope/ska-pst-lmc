
Helm chart
==========

This is a summary of the Helm chart parameters that can be used to customise
the PST.LMC deployment. The current default values can be found in the chart's
`values file`_.


Configuration database
----------------------

The configuration database is implemented on top of `etcd`_.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``etcd.image``
    - etcd container image
    - ``quay.io/coreos/etcd``
  * - ``etcd.version``
    - etcd container version
    - ``3.3.27``
  * - ``etcd.imagePullPolicy``
    - etcd container image pull policy
    - ``IfNotPresent``
  * - ``etcd.replicas``
    - Number of etcd server replicas
    - ``1``
  * - ``etcd.persistence.enabled``
    - Enable persistence of etcd database in persistent volume claim
    - ``false``
  * - ``etcd.persistence.size``
    - Size of persistent volume claim
    - ``1Gi``
  * - ``etcd.persistence.storageClassName``
    - Storage class name for persistent volume claim
    - ``standard``
  * - ``etcd.persistence.autoCompaction.retention``
    -  Auto compaction retention for key-value store in hours
    - ``0``
  * - ``etcd.persistence.autoCompaction.mode``
    -  Auto compaction mode
    - ``periodic``
  * - ``etcd.persistence.defrag.enabled``
    -  Enable periodic etcd defragmentation
    - ``false``
  * - ``etcd.persistence.defrag.cronjob.schedule``
    -  Schedule in Cron format for etcd defragmentation
    - ``30 23 * * 3,7``
  * - ``etcd.persistence.defrag.cronjob.historyLimit``
    -  Number of successful finished jobs to retain
    - ``1``
  * - ``etcd.maxTxnOps``
    -  Maximum number of operations per transaction
    - ``1024``


Console
-------

The console provides a command-line interface to monitor and control the PST.LMC by
interacting with the configuration database.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``console.enabled``
    - Enable the console
    - ``true``
  * - ``console.image``
    - Console container image
    - ``artefact.skao.int/ska-pst-console``
  * - ``console.version``
    - Console container version
    - See `values file`_
  * - ``console.imagePullPolicy``
    - Console container image pull policy
    - ``IfNotPresent``


Operator web interface
----------------------

The operator web interface can be used to control and monitor the pst by
interacting with the configuration database.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``opinterface.enabled``
    - Enable the operator web interface
    - ``true``
  * - ``opinterface.image``
    - Operator web interface container image
    - ``artefact.skao.int/ska-pst-opinterface``
  * - ``opinterface.version``
    - Operator web interface container version
    - See `values file`_
  * - ``opinterface.imagePullPolicy``
    - Operator web interface container image pull policy
    - ``IfNotPresent``


Processing controller
---------------------

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``proccontrol.image``
    - Processing controller container image
    - ``artefact.skao.int/ska-pst-proccontrol``
  * - ``proccontrol.version``
    - Processing controller container version
    - See `values file`_
  * - ``proccontrol.imagePullPolicy``
    - Processing controller container image pull policy
    - ``IfNotPresent``


Processing scripts
------------------

Processing script definitions to be used by PST.LMC. These map the script kind,
name and version to a container image. By default the definitions are read from
the `scripts repository`_ in GitLab. A different URL may be specified.
Alternatively a list of script definitions can be passed to the chart.

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Description
    - Default
  * - ``scripts.url``
    - URL from which to read the script definitions
    - ``https://gitlab.com/ska-telescope/pst/ska-pst-script/-/raw/master/scripts.json``
  * - ``scripts.definitions``
    - List of script definitions. If present, used instead of the URL. See the example below
    - Not set

Example of script definitions in a values file:

.. code-block:: yaml

  scripts:
    definitions:
    - type: realtime
      id: test-realtime
      version: 0.3.0
      image: artefact.skao.int/ska-pst-script-test-batch:0.3.0
    - type: batch
      id: test-batch
      version: 0.3.0
      image: artefact.skao.int/ska-pst-script-test-realtime:0.3.0


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