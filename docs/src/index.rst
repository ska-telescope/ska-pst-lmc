.. skeleton documentation master file, created by
   sphinx-quickstart on Thu May 17 15:17:35 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


.. HOME SECTION ===========================================================

.. Hidden toctree to manage the sidebar navigation.

SKA PST LMC - Local Monitoring and Control
==========================================

This site documents the Local Monitoring and Control (LMC) software
of the Pulsar Timing Sub-element (PST) within the Central Signal Processor
(CSP) Element of the Square Kilometre Array (SKA) Low and Mid telescopes.

In addition to the notes for developers of the PST.LMC software, this
documentation includes

- an overview of the LMC architecture;
- installation and deployment instructions;
- instructions for testing PST.LMC in simulation mode;
- the LMC library internal API (for PST LMC developers);
- the PST.LMC TANGO API (properties, commands, and attributes);


For a description of the fully-integrated PST, please see the ska-pst-integration_ documentation.

.. _ska-pst-integration: https://www.python.org/

.. Architecture ===========================================================

.. toctree::
  :caption: Architecture
  :maxdepth: 2

  Overview<architecture/index>
  Devices<architecture/devices>
  Integration<architecture/integration>

.. Deployment =============================================================

.. toctree::
  :caption: Deployment
  :maxdepth: 2

  Overview<deployment/index>
  deployment/requirements
  deployment/standalone
  deployment/using-make
  deployment/helm-chart

.. Operation ==============================================================

.. toctree::
  :caption: Operation
  :maxdepth: 2

  operation/itango
  operation/troubleshooting


.. Development ============================================================

.. toctree::
  :caption: Development
  :maxdepth: 2

  Gitlab README<../../README>

.. API ====================================================================

.. automodule:: ska_pst_lmc

.. toctree::
  :caption: API
  :maxdepth: 2

  PST.LMC (TANGO) API<api/tango>
  Internal (Python) API<api/index>
