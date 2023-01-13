.. _development_deployment:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Development deployment
======================

This page describes how to install, interact with, and uninstall development
versions of PST.LMC using ``make`` commands that are run from the root directory 
of the ska-pst-lmc git repository.

Configure environment
---------------------

First clone the repo and submodules to your local file system

.. code-block:: bash

    git clone --recursive git@gitlab.com:ska-telescope/pst/ska-pst-lmc.git
    cd ska-pst-lmc

The following environment variables control the deployment and testing of the PST.LMC:

.. list-table::
  :widths: auto
  :header-rows: 1

  * - Environment variable
    - Default value
    - Description
  * - ``KUBE_NAMESPACE``
    - ``pst``
    - Kubernetes namespace for deployment
  * - ``K8S_CHART``
    - ``test-parent``
    - Name of the Helm chart to be installed; for simulation mode, use ska-pst-lmc 

Deploy PST.LMC
--------------

Deploy PST.LMC into the default ``pst`` namespace in simulation mode.

.. code-block:: console

    $ export K8S_CHART=ska-pst-lmc
    $ make k8s-install-chart

Interact with PST.LMC
---------------------

See :ref:`Operation / Using itango <operation_itango>` for an example of interacting with PST.LMC via itango.

Shut down PST.LMC
-----------------

When finished with PST.LMC, clean up the deployment.

.. code-block:: console

    $ make k8s-uninstall-chart

