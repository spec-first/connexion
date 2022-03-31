Command-Line Interface
======================
For convenience Específico provides a command-line interface
(CLI). This interface aims to be a starting point in developing or
testing OpenAPI specifications with Específico.

The available commands are:

- ``especifico run``

All commands can run with -h or --help to list more information.

Running an OpenAPI specification
--------------------------------

The subcommand ``run`` of Específico's CLI makes it easy to run OpenAPI
specifications directly even before any operation handler function gets
implemented. This allows you to verify and inspect how your API will
work with Específico.

To run your specification, execute in your shell:

.. code-block:: bash

     $ especifico run your_api.yaml --stub --debug

This command will tell Específico to run the ``your_api.yaml``
specification file attaching a stub operation (``--stub``) to the
unavailable operations/functions of your API and in debug mode
(``--debug``).

The basic usage of this command is:

.. code-block:: bash

    $ especifico run [OPTIONS] SPEC_FILE [BASE_MODULE_PATH]

Where:

- SPEC_FILE: Your OpenAPI specification file in YAML format.
- BASE_MODULE_PATH (optional): filesystem path where the API endpoints
  handlers are going to be imported from. In short, where your Python
  code is saved.

There are more options available for the ``run`` command, for a full
list run:

.. code-block:: bash

     $ especifico run --help

Running a mock server
---------------------

You can run a simple server which returns example responses on every request.
The example responses must be defined in the ``examples`` response property of the OpenAPI specification.
Your API specification file is not required to have any ``operationId``.

.. code-block:: bash

    $ especifico run your_api.yaml --mock=all -v
