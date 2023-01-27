.. _release_deployment:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Release deployment
==================

This page describes how to install, interact with, and uninstall 
released versions of PST.LMC using helm, kubectl, and the itango console.

Configure environment
---------------------

If running in a local kubernetes environment, either use the default namespace or create a namespace; e.g.

.. code-block:: console

    $ kubectl create namespace pst

Configure the namespace used by ``helm`` and ``kubectl``:

.. code-block:: console

    $ export HELM_NAMESPACE=pst
    $ kubectl config set-context --current --namespace=pst

In the following, it is assumed that the namespace is either the default
or configured appropriately.

Deploy PST.LMC
--------------

Released versions of PST Helm charts are published in the SKAO artefact repository. 
To install a released version, first add this chart repository to helm:

.. code-block:: console

    $ helm repo add ska https://artefact.skao.int/repository/helm-internal

If the SKAO repository has already been added, update to gain access to latest chart versions:

.. code-block:: console

    $ helm repo update

Check to see that the PST.LMC chart is available:

.. code-block:: console

    $ helm search repo ska/ska-pst-lmc

Deploy PST.LMC in simulation mode:

.. code-block:: console

    $ helm install ska-pst-lmc ska/ska-pst-lmc

Watch the deployment in progress using either the ``k9s`` terminal-based UI (recommended) or ``kubectl``:

.. code-block:: console

    $ kubectl get pod --watch

Wait until all the pods are Running or Completed:

.. code-block:: none

    NAME                                    READY   STATUS      RESTARTS   AGE
    databaseds-tango-base-test-0            1/1     Running     0          48s
    low-pst-beam-01-0                       1/1     Running     0          48s
    low-pst-beam-ska-pst-lmc-config-ndg62   0/1     Completed   0          48s
    ska-tango-base-tangodb-0                1/1     Running     0          48s
    tangotest-ska-pst-lmc-config-gnqtg      0/1     Completed   0          48s
    tangotest-test-0                        1/1     Running     0          48s

You can check the logs of pods to verify that they are doing okay:

.. code-block:: console

    $ kubectl logs <pod_name>

For example, 

.. code-block:: console

    $ kubectl logs low-pst-beam-01-0 | grep OK

should show that ``dsp``, ``recv``, ``smrb``, and ``beam`` have successfully completed initialisation:

.. code-block:: none

    1|2023-01-12T23:39:06.903Z|INFO|MainThread|do|obs_device.py#54|tango-device:low-pst/dsp/01|SKAObsDevice Init command completed OK
    1|2023-01-12T23:39:06.903Z|INFO|MainThread|do|obs_device.py#222|tango-device:low-pst/dsp/01|CspSubElementObsDevice Init command completed OK
    1|2023-01-12T23:39:07.005Z|INFO|MainThread|do|obs_device.py#54|tango-device:low-pst/recv/01|SKAObsDevice Init command completed OK
    1|2023-01-12T23:39:07.005Z|INFO|MainThread|do|obs_device.py#222|tango-device:low-pst/recv/01|CspSubElementObsDevice Init command completed OK
    1|2023-01-12T23:39:07.203Z|INFO|MainThread|do|obs_device.py#54|tango-device:low-pst/smrb/01|SKAObsDevice Init command completed OK
    1|2023-01-12T23:39:07.203Z|INFO|MainThread|do|obs_device.py#222|tango-device:low-pst/smrb/01|CspSubElementObsDevice Init command completed OK
    1|2023-01-12T23:39:07.309Z|INFO|MainThread|do|obs_device.py#54|tango-device:low-pst/beam/01|SKAObsDevice Init command completed OK
    1|2023-01-12T23:39:07.309Z|INFO|MainThread|do|obs_device.py#222|tango-device:low-pst/beam/01|CspSubElementObsDevice Init command completed OK

Interact with PST.LMC
---------------------

By default, the ``ska-pst-lmc`` chart does not deploy the iTango shell pod from the
``ska-tango-base`` chart. To enable it:

.. code-block:: console

    $ helm upgrade ska-pst-lmc ska/ska-pst-lmc --set ska-tango-base.itango.enabled=true

See :ref:`Operation / Using itango <operation_itango>` for an example of interacting with PST.LMC via itango.

Shut down PST.LMC
-----------------

To remove the PST.LMC deployment from the cluster:

.. code-block:: console

    $ helm uninstall ska-pst-lmc

