.. _running_requirements:

Requirements
============

To run the PST.LMC, you need to have `Kubernetes <https://kubernetes.io/>`_ and
`Helm <https://helm.sh>`_ installed.

Kubernetes
----------

Local development using Minikube
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Locally, minikube can be started with the default configuration by running:

.. code-block:: console

    $ minikube start

If you are developing PST.LMC components and you would like to build and test them
in Minikube, you need to configure Docker to use the daemon inside the VM.
This can be done by setting the environment variables:

.. code-block:: console

    $ minikube docker-env
    $ eval $(minikube -p minikube docker-env)

Remote Kubernetes
^^^^^^^^^^^^^^^^^
Alternatively, it is possible to install and interact with a PST.LMC instance
on a remote Kubernetes cluster.

To do this, you will need to obtain the Cluster access credentials as a file on 
the local filesystem and activate them as in this example:

.. code-block:: console

    $ export KUBECONFIG=~/dp-orca.yaml

If the credentials are valid, local commands (such as kubectl or helm) will
execute on the remote cluster.

Helm
----

Helm is available from most typical package managers, see `Introduction to Helm
<https://helm.sh/docs/intro/>`_.


K9s
---

`K9s <https://k9scli.io>`_ is terminal-based UI for Kubernetes clusters which
provides a convenient interactive interface. It is not required to run the PST.LMC,
but it is recommended for its ease of use.


Commands Help Guide
-------------------

To find out more about the available commands, here are some useful links:

* Helm - `<https://helm.sh/docs/helm/helm/>`_
* Kubectl - `<https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands>`_
* Docker  - `<https://docs.docker.com/engine/reference/commandline/cli/>`_
* Podman - `<https://podman.io/>`_
