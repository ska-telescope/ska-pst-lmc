.. _running_standalone:

Stand-alone deployment
======================

Before running the PST.LMC, your local development environment needs to be set up. 
This can either be a local Kubernetes instance running in Minikube or by using 
remote access to a Kubernetes cluster.
Details can be found in the :ref:`requirements <running_requirements>` section.

In this page, we describe how you can install, test, interact with, and uninstall 
PST.LMC using helm, kubectl, and the itango console.

The ska-pst-lmc repository provides a Makefile, which simplifies
some of these steps, including installing and uninstalling the PST.LMC,
and running integration tests:

  :ref:`using-make`

Create the namespace for PST.LMC processing
-------------------------------------------

If you are using a local environment, you may use the default namespace for the control
system.
Below, when we provide commands for local development, this namespace is assumed to
be called ``pst``. In examples using remote Kubernetes the placeholder is ``<pst-namespace>``:

.. code-block:: console

    $ kubectl create namespace pst

For remote Kubernetes clusters namespaces may be pre-assigned and, if so, 
we will show the modifications to allow commands to use such namespaces.

Deploying the PST.LMC
---------------------

Releases of the PST.LMC Helm chart are published in the SKA artefact repository. To
install the released version, you need to add this chart repository to helm:

.. code-block:: console

    $ helm repo add ska https://artefact.skao.int/repository/helm-internal

If you already have the repository, you can update it, in order to gain
access to latest chart versions, using:

.. code-block:: console

    $ helm repo update

The chart can be installed with the command (assuming the release name is ``test``):

.. code-block:: console

    $ helm install test ska/ska-pst

Or with non-default namespace names:

.. code-block:: console

    $ helm install test ska/ska-pst -n <namespace> --set helmdeploy.namespace=<pst-namespace>

You can watch the deployment in progress using ``kubectl``:

.. code-block:: console

    $ kubectl get pod -n <namespace> --watch

or the ``k9s`` terminal-based UI (recommended):

.. code-block:: console

    $ k9s

Wait until all the pods are running:

.. code-block:: console

     default      databaseds-tango-base-test-0      ●  1/1          0 Running    172.17.0.12     m01   119s
     default      ska-pst-console-0                 ●  1/1          0 Running    172.17.0.15     m01   119s
     default      ska-pst-etcd-0                    ●  1/1          0 Running    172.17.0.6      m01   119s
     default      ska-pst-helmdeploy-0              ●  1/1          0 Running    172.17.0.14     m01   119s
     default      ska-pst-lmc-config-6vbtr          ●  0/1          0 Completed  172.17.0.11     m01   119s
     default      ska-pst-lmc-controller-0          ●  1/1          0 Running    172.17.0.9      m01   119s
     default      ska-pst-lmc-subarray-01-0         ●  1/1          0 Running    172.17.0.10     m01   119s
     default      ska-tango-base-tangodb-0          ●  1/1          0 Running    172.17.0.8      m01   119s

The two pods with ``config`` in their name will vanish about 30 seconds after they complete.

You can check the logs of pods to verify that they are doing okay:

.. code-block:: console

    $ kubectl logs <pod_name> -n <namespace>

or for a non-default namespace:

.. code-block:: console

    $ kubectl logs <pod_name> -n <namespace>

For example:

.. code-block:: console

    $ kubectl logs ska-pst-lmc-subarray-01-0
    ...
    1|2021-05-25T11:32:53.161Z|INFO|MainThread|init_device|subarray.py#92|tango-device:test-pst/subarray/01|pst Subarray initialising
    ...
    1|2021-05-25T11:32:53.185Z|INFO|MainThread|init_device|subarray.py#127|tango-device:test-pst/subarray/01|pst Subarray initialised
    ...
    $ kubectl logs ska-pst-proccontrol-0
    1|2021-05-25T11:32:32.423Z|INFO|MainThread|main_loop|processing_controller.py#180||Connecting to config DB
    1|2021-05-25T11:32:32.455Z|INFO|MainThread|main_loop|processing_controller.py#183||Starting main loop
    1|2021-05-25T11:32:32.566Z|INFO|MainThread|main_loop|processing_controller.py#190||processing block ids []
    ...

If it looks like this, there is a good chance everything has been deployed correctly.

Testing it out
--------------

Connecting to the configuration database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``ska-pst`` chart deploys a 'console' pod which enables you to interact with the
configuration database. You can start a shell in the pod by doing:

.. code-block:: console

    $ kubectl exec -it ska-pst-console-0 -n <namespace> -- bash

This will allow you to use the ``ska-pst`` command:

.. code-block:: console

    # ska-pst list -a
    Keys with prefix /:
    /lmc/controller
    /lmc/subarray/01
    /script/batch:test-batch:0.3.0
    ...

Which shows that the configuration contains the state of the Tango devices and
the processing script definitions.

Details about the existing commands of the ``ska-pst`` utility can be found in the
`CLI to interact with pst <https://developer.skao.int/projects/ska-pst-config/en/latest/cli.html>`_
section in the pst Configuration Library documentation.

Starting a processing script
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Next, we can add a processing block to the configuration:

.. code-block:: console

    # ska-pst create pb <script-kind>:<script-name>:<script-version>

For example

.. code-block:: console

    # ska-pst create pb batch:test-dask:0.3.0
    Processing block created with pb_id: pb-pstcli-20221011-00000

The processing block is created with the ``/pb`` prefix in the
configuration:

.. code-block:: console

    # ska-pst list -v pb
    Keys with prefix /pb:
    /pb/pb-pstcli-20221011-00000 = {
      "dependencies": [],
      "eb_id": null,
      "parameters": {},
      "pb_id": "pb-pstcli-20221011-00000",
      "script": {
        "kind": "batch",
        "name": "test-dask",
        "version": "0.3.0"
      }
    }
    /pb/pb-pstcli-20221011-00000/owner = {
      "command": [
        "test_dask.py"
      ],
      "hostname": "proc-pb-pstcli-20221011-00000-script--1-qqvgw",
      "pid": 1
    }
    /pb/pb-pstcli-20221011-00000/state = {
      "deployments": {
        "proc-pb-pstcli-20221011-00000-dask-1": "RUNNING",
        "proc-pb-pstcli-20221011-00000-dask-2": "RUNNING"
      },
      "last_updated": "2022-10-11 08:20:34",
      "resources_available": true,
      "status": "RUNNING"
    }

The processing block is detected by the processing controller which deploys the
script. The script in turn deploys the execution engines (in this case, Dask).
The deployments are requested by creating entries with ``/deploy`` prefix in
the configuration database, where they are detected by the Helm deployer
which actually makes the deployments:

.. code-block:: console

    # ska-pst list -v deployment
    Keys with prefix /deploy:
    /deploy/proc-pb-pstcli-20221011-00000-dask-1 = {
      "args": {
        "chart": "dask",
        "values": {
          "image": "artefact.skao.int/ska-pst-script-test-dask:0.3.0",
          "worker.replicas": 2
        }
      },
      "dpl_id": "proc-pb-pstcli-20221011-00000-dask-1",
      "kind": "helm"
    }
    /deploy/proc-pb-pstcli-20221011-00000-dask-1/state = {
      "pods": {
        "proc-pb-pstcli-20221011-00000-dask-1-scheduler-7d6f5f9749-vr6dw": "Running",
        "proc-pb-pstcli-20221011-00000-dask-1-worker-5744899988-hmr5q": "Running",
        "proc-pb-pstcli-20221011-00000-dask-1-worker-5744899988-sqnf6": "Running"
      }
    }
    /deploy/proc-pb-pstcli-20221011-00000-dask-2 = {
      "args": {
        "chart": "dask",
        "values": {
          "image": "artefact.skao.int/ska-pst-script-test-dask:0.3.0",
          "worker.replicas": 2
        }
      },
      "dpl_id": "proc-pb-pstcli-20221011-00000-dask-2",
      "kind": "helm"
    }
    /deploy/proc-pb-pstcli-20221011-00000-dask-2/state = {
      "pods": {
        "proc-pb-pstcli-20221011-00000-dask-2-scheduler-65cc58cf4f-8bm9r": "Running",
        "proc-pb-pstcli-20221011-00000-dask-2-worker-79694dbf85-j7nfb": "Running",
        "proc-pb-pstcli-20221011-00000-dask-2-worker-79694dbf85-njw6c": "Running"
      }
    }
    /deploy/proc-pb-pstcli-20221011-00000-script = {
      "args": {
        "chart": "script",
        "values": {
          "env": [
            {
              "name": "pst_CONFIG_HOST",
              "value": "ska-pst-etcd-client.dp-orca"
            },
            {
              "name": "pst_HELM_NAMESPACE",
              "value": "dp-orca-p"
            },
            {
              "name": "pst_PB_ID",
              "value": "pb-pstcli-20221011-00000"
            }
          ],
          "image": "artefact.skao.int/ska-pst-script-test-dask:0.3.0"
        }
      },
      "dpl_id": "proc-pb-pstcli-20221011-00000-script",
      "kind": "helm"
    }
    /deploy/proc-pb-pstcli-20221011-00000-script/state = {
      "pods": {
        "proc-pb-pstcli-20221011-00000-script--1-r4p9c": "Running"
      }
    }


The deployments associated with the processing block have been created
in the ``pst`` namespace. You can list the running pods using kubectl
on the host (exit the console pod):

.. code-block:: console

    $ kubectl get pod -n <pst-namespace>
    NAME                                                              READY   STATUS    RESTARTS   AGE
    proc-pb-pstcli-20221011-00000-dask-1-scheduler-7d6f5f9749-vr6dw   1/1     Running     0          9s
    proc-pb-pstcli-20221011-00000-dask-1-worker-5744899988-hmr5q      1/1     Running     0          9s
    proc-pb-pstcli-20221011-00000-dask-1-worker-5744899988-sqnf6      1/1     Running     0          9s
    proc-pb-pstcli-20221011-00000-dask-2-scheduler-65cc58cf4f-8bm9r   1/1     Running     0          10s
    proc-pb-pstcli-20221011-00000-dask-2-worker-79694dbf85-j7nfb      1/1     Running     0          10s
    proc-pb-pstcli-20221011-00000-dask-2-worker-79694dbf85-njw6c      1/1     Running     0          10s
    proc-pb-pstcli-20221011-00000-script--1-r4p9c                     1/1     Running     0          14s

Cleaning up
^^^^^^^^^^^

Finally, let us remove the processing block from the configuration (in the pst
console shell):

.. code-block:: console

    # ska-pst delete pb pb-pstcli-20221011-00000
    /pb/pb-pstcli-20221011-00000
    /pb/pb-pstcli-20221011-00000/state
    Deleted above keys with prefix /pb/pb-pstcli-20221011-00000.

If you re-run the commands from the last section you will notice that
this correctly causes all changes to the cluster configuration to be
undone as well.

Accessing the Tango interface
-----------------------------

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

.. code-block:: python

    In [2]: d = DeviceProxy('test-pst/subarray/01')

    In [3]: d.state()
    Out[3]: tango._tango.DevState.OFF

    In [4]: d.On()

    In [5]: d.state()
    Out[5]: tango._tango.DevState.ON

    In [6]: d.obsState
    Out[6]: <obsState.EMPTY: 0>

To start processing on PST.LMC, you will need a configuration string, which provides the set up, the request for 
resources, and the request of what processing script to run. You can find an example string in the `Tango Jupyter 
notebook <https://gitlab.com/ska-telescope/pst/ska-pst-notebooks/-/blob/main/src/ska-pst-tango-tutorial.ipynb>`_ (the 
configuration string can be found `here 
<https://gitlab.com/ska-telescope/pst/ska-pst-notebooks/-/blob/main/src/ska-pst-tango-tutorial.ipynb?plain=1#L228>`_,
we recommend that you copy it from the display-version of the notebook and not the raw file).

Save the copied configuration string (which is provided as JSON in the example notebook) as
a python string. Make sure you update the execution block and processing block IDs
(if you run this multiple times, you will need to increment the number at the end):

.. code-block:: python

    import json
    EXECUTION_BLOCK_ID = f"eb-test-20221012-00001"
    PROCESSING_BLOCK_ID_REALTIME = f"pb-testrealtime-20221012-00001"
    PROCESSING_BLOCK_ID_BATCH = f"pb-testbatch-20221012-00001"

    config = json.dumps(<copied-json-string>)


In addition more details about the PST.LMC Subarray Tango commands
and examples of valid control strings can be found in the `Subarray section of PST.LMC LMC
<https://developer.skao.int/projects/ska-pst-lmc/en/latest/pst-subarray.html>`_.

The `Telescope Model library <https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-pst.html>`_
provides detailed explanation of configurations strings for each PST.LMC command.

Below, we provide the steps from assigning resources to the processing,
through configure and scan, to releasing the resources and ending the process.

.. code-block:: python

    In [8}: d.AssignResources(config)

    In [9]: d.obsState
    Out[9]: <obsState.IDLE: 0>

    In [10]: d.Configure('{"interface": "https://schema.skao.int/ska-pst-configure/0.4", "scan_type": "target:a"}')

    In [11]: d.obsState
    Out[11]: <obsState.READY: 2>

    In [12]: d.Scan('{"interface": "https://schema.skao.int/ska-pst-scan/0.4", "scan_id": 1}')

    In [13]: d.obsState
    Out[13]: <obsState.SCANNING: 3>

    In [14]: d.EndScan()

    In [15]: d.obsState
    Out[15]: <obsState.READY: 2>

    In [16]: d.End()

    In [17]: d.obsState
    Out[17]: <obsState.IDLE: 0>

    In [18]: d.ReleaseResources('{ "interface": "https://schema.skao.int/ska-pst-releaseres/0.4", '
                   '"resources": {"receptors": ["SKA001", "SKA002", "SKA003", "SKA004"]}}')

    In [19]: d.obsState
    Out[19]: <obsState.EMPTY: 0>

    In [20]: d.Off()

    In [21]: d.state()
    Out[21]: tango._tango.DevState.OFF

ReleaseResources takes the list of resources ("receptors") to be released. If you
want to release all of them at once, you may use ``d.ReleaseAllResources()``.

Removing the PST.LMC
--------------------

To remove the PST.LMC deployment from the cluster, do:

.. code-block:: console

    $ helm uninstall test
