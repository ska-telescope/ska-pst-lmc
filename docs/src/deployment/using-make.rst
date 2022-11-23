.. _using-make:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Using `make` to deploy and test
===============================

First clone the repo and submodules to your local file system

    git clone --recursive git@gitlab.com:ska-telescope/pst/ska-pst-lmc.git
    cd ska-pst-lmc

The ska-pst-lmc repository contains a
`Makefile <https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/blob/main/Makefile>`_
which provides targets to simplify deploying and testing the PST.LMC.
The following commands should be run from the root directory of
the git repository.

Environment variables
---------------------

The environment variables to control the deployment and testing of the PST.LMC are
defined at the top of the Makefile. They are described in the table below.

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

To use values that differ from the defaults, either set the environment variables
or use them together with the commands.

For example:

.. code-block:: console

    $ export K8S_CHART=ska-pst-lmc
    $ make k8s-install-chart 

The above will install PST.LMC into the default ``pst`` namespace in simulation mode.

Deploying the PST.LMC
---------------------

.. code-block:: console

    $ make k8s-install-chart

By default, the PST.LMC will be installed using the local copy of the Helm chart in
the ``charts`` directory.

If instead you want to use the published version of the PST.LMC chart from the SKA
Central Artefact Repository, then add the Helm chart repository

.. code-block:: console

    $ helm repo add ska https://artefact.skao.int/repository/helm-internal

and install PST.LMC using this repository?

:red:`Ask Jes and/or Will how to do this ... see sdp-integration doco`


Running the integration tests
-----------------------------

The PST.LMC repository includes several tests that verify the system behaviour.
These can be found in the
`tests <https://gitlab.com/ska-telescope/pst/ska-pst-lmc/-/tree/master/tests>`_ directory,
together with BDD scenarios and resources to run the tests.

You can run the tests with

.. code-block:: console

    $ make ???

Cleaning up and removing PST.LMC
--------------------------------

Once finished with PST.LMC, you can use the following
commands to clean up your deployment.

Uninstall PST.LMC:

.. code-block:: console

    $ make uninstall-pst
    
