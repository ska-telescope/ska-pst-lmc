.. _example_schema:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

PST Schema
==========

The arguments of the ``configure`` and ``scan`` commands include strings
containing data in JSON format. The data are described by schema which are
versioned to support evolution of the interfaces. A specific scheme is 
specified with the ``interface`` keyword in the JSON string:

.. code-block:: json

  {
    "interface": "https://schema.skao.int/ska-pst-<interface>/<version>",
    "...": "..."
  }

where ``<interface>`` identifies the command or attribute:

- ``configure`` - Configure command
- ``scan`` - Scan command

and ``<version>`` is the version of the scheme.

The JSON string can be validated against the scheme using the `telescope model
library <https://developer.skao.int/projects/ska-telmodel/en/latest/>`_. Its
documentation describes the versions of the schema. The PST.BEAM device
implements version :red:`0.4` of the schemas, which is used in the examples below.

:red:`Do we want to include anything about the CSP sub-element device here?`

The commands will accept arguments in versions 0.2 and 0.3 of the schemas for
backwards compatibility. If a command argument does not have an ``interface``
value, it defaults to version 0.2 (this was the last version before
``interface`` values were used routinely).

:red:`Include links to example JSON strings that can be cut and pasted into itango?`

