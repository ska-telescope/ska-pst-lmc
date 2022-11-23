.. _running_standalone:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Stand-alone deployment
======================

Before running the PST.LMC, your local development environment needs to be set up. 
This can either be a local Kubernetes instance running in Minikube or by using 
remote access to a Kubernetes cluster.
Details can be found in the :ref:`requirements <running_requirements>` section.

In this page, we describe how you can install, test, interact with, and uninstall 
PST.LMC using helm, kubectl, and the itango console.

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

:red:`Replace the following snippet with one from example PST.LMC use`

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

    $ kubectl logs <pod_name>

or for a non-default namespace:

.. code-block:: console

    $ kubectl logs <pod_name> -n <namespace>

For example:

:red:`Replace the following snippet with one from example PST.LMC use`

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

Removing the PST.LMC
--------------------

To remove the PST.LMC deployment from the cluster, do:

.. code-block:: console

    $ helm uninstall test
