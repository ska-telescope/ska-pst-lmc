.. _using-make:

Using `make` to deploy and test
===============================

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
    - ``test``
    - Kubernetes namespace for deploying the control system
  * - ``KUBE_NAMESPACE_pst``
    - ``test-pst``
    - Kubernetes namespace for deploying the processing scripts
  * - ``HELM_RELEASE``
    - ``test``
    - Name of the Helm chart release
  * - ``HELM_REPO``
    - ``charts``
    - Location of the Helm chart repository, may be a directory or name of a remote repository
  * - ``HELM_VALUES``
    - ``resources/test.yaml``
    - Values file(s) to use to install/upgrade the PST.LMC deployment, may be a list of files separated by spaces
  * - ``TEST_INGRESS``
    - ``http://$(shell minikube ip)``
    - Ingress to use to execute tests. The default value assumes a Minikube cluster is being used
  * - ``TEST_TANGO_CLIENT``
    - ``gql``
    - Client to use to connect to Tango devices in the tests
  * - ``TEST_MARKER``
    - ``"not deployment_failure"``
    - Pytest markers to be used in the tests

If you are using different values from the default ones, you will have to
export the environment variables, or use them together with the commands.
Alternatively, you can temporarily update the Makefile, but make sure
you are working from a branch so that you don't accidentally commit your changes.

For example:

.. code-block:: console

    $ export KUBE_NAMESPACE=default
    $ export KUBE_NAMESPACE_pst=pst

    $ make install-pst

The above will install PST.LMC into the ``default`` namespace and use the ``pst`` namespace
for processing script deployments.

Creating namespaces
-------------------

Create the namespaces specified in the environment variables with:

.. code-block:: console

    $ make create-namespaces

Updating chart dependencies
---------------------------

If you're using the local copy of the chart to install PST.LMC, you can make sure
you have the latest chart dependencies available with:

.. code-block:: console

    $ make update-chart-dependencies

Deploying the PST.LMC
---------------------

.. code-block:: console

    $ make install-pst

By default, the PST.LMC will be installed using the local copy of the Helm chart in
the ``charts`` directory.

If instead you want to use the published version of the PST.LMC chart from the SKA
Central Artefact Repository, then you can do that using the ``HELM_REPO``
variable. First, add the Helm chart repository:

.. code-block:: console

    $ helm repo add ska https://artefact.skao.int/repository/helm-internal

Then install PST.LMC using this repository:

.. code-block:: console

    $ HELM_REPO=ska make install-pst

The ``install-pst`` command upgrades the deployment if it exists,
or installs it if it doesn't. It has a ``--wait`` switch added to it,
which means the command will only return once the deployment has
finished installing/upgrading.

Running the integration tests
-----------------------------

The Integration GitLab repository contains several tests, which make
sure the PST.LMC system behaves as expected. These can be found in the
`tests <https://gitlab.com/ska-telescope/pst/ska-pst-integration/-/tree/master/tests>`_ directory,
together with BDD scenarios and resources to run the tests.

The tests are marked with pytest markers. The ``TEST_MARKER`` environment variable
specifies which tests will run when using the make targets. For example, if you
only want to run the visibility receive test, you would need to use
``TEST_MARKER="visibility_receive"``.

The tests interact with the Tango devices via `Tango GraphQL
<https://gitlab.com/ska-telescope/external/tangogql>`_. You need to install
this chart first:

.. code-block:: console

    $ make install-test-tangogql

.. note::

    If you are using Minikube with the docker driver, then you must enable
    tunnelling for the tests to work, which is done by running this command in
    a separate terminal:

    .. code-block:: console

        $ minikube tunnel

    It may ask you for an administrator password to open privileged ports. The
    command must remain running for the tunnel to be active. You must also set
    the ingress URL to point to localhost:

    .. code-block:: console

        $ export TEST_INGRESS=http://127.0.0.1

Once the Tango GraphQL pod is started, you can run the tests with

.. code-block:: console

    $ make test

Note: by default all tests are run, including the visibility
receive one, except the component failure tests.

The visibility receive test requires a couple of helper pods,
which connect to persistent volumes. These contain
MeasurementSet data (stored using Git LFS in the repository,
see :ref:`troubleshooting`),
which are used for sending and validating the received data.
These pods are automatically created and removed by the test,
however, for manual testing purposes, you may want to create
them yourself:

.. code-block:: console

    $ make create-test-volumes

Finally, run the visibility receive test:

.. code-block:: console

    $ TEST_MARKER="visibility_receive" make test

Cleaning up and removing PST.LMC
--------------------------------

Once you finished work with PST.LMC, you can use the following
commands to clean up your deployment.

Remove resources used for tests:

.. code-block:: console

    $ make delete-test-volumes
    $ make uninstall-test-tangogql

Uninstall PST.LMC:

.. code-block:: console

    $ make uninstall-pst

Delete namespaces (optional)

.. code-block:: console

    $ make delete-namespaces
