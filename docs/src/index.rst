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

For a description of the fully-integrated PST, please see the ska-pst-integration_ documentation.

.. _ska-pst-integration: https://developer.skao.int/projects/ska-pst-integration/en/latest/

.. Architecture ===========================================================

.. toctree::
  :caption: Architecture
  :maxdepth: 2

  Devices<architecture/devices>
  Integration<architecture/integration>

.. Deployment =============================================================

.. toctree::
  :caption: Deployment
  :maxdepth: 2

  deployment/requirements
  deployment/release
  deployment/development
  deployment/helm-chart

.. Operation ==============================================================

.. toctree::
  :caption: Operation
  :maxdepth: 2

  operation/itango
  operation/troubleshooting

.. API ====================================================================

.. toctree::
  :caption: TANGO API
  :maxdepth: 2

  api/tango

.. Development ============================================================

.. automodule:: ska_pst_lmc

.. toctree::
  :caption: Development
  :maxdepth: 2

  Gitlab README<../../README>
  api/devices
  Internal API<api/index>
