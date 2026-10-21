Command-Line Interface
======================
For convenience, Connexion provides a command-line interface (CLI). 
This interface serves as a starting point for developing or testing 
OpenAPI specifications with Connexion.

Running an OpenAPI specification
--------------------------------

The ``run`` subcommand of Connexion's CLI makes it easy to run OpenAPI 
specifications directly, even before any operation handler functions are 
implemented.

To run your specification, execute in your shell:

.. code-block:: bash

    $ connexion run your_api.yaml --stub

This command will tell Connexion to run the ``your_api.yaml``
specification file attaching a stub operation (``--stub``) to the
unavailable operations/functions of your API, which will return a ``501 Not Implemented`` response.

The basic usage of this command is:

.. code-block:: bash

    $ connexion run [OPTIONS] SPEC_FILE [BASE_MODULE_PATH]

Where:

- SPEC_FILE: Your OpenAPI specification file in YAML format. Can also be given
  as a URL, which will be automatically downloaded.
- BASE_MODULE_PATH (optional): file system path from which the API endpoint 
  handlers will be imported. In short, where your Python code is saved.

There are more options available for the ``run`` command, for a full
list run:

.. code-block:: bash

    $ connexion run --help

Running a mock server
---------------------

You can run a simple server which returns example responses on every request.

The example responses can be defined in the ``examples`` response property of
the OpenAPI specification. If no examples are specified, and you have installed Connexion with the `mock` extra (``pip install connexion[mock]``), an example is generated based on the provided schema.

Your API specification file does not need to have any ``operationId``.

.. code-block:: bash

    $ connexion run your_api.yaml --mock=all

    $ connexion run https://raw.githubusercontent.com/spec-first/connexion/main/examples/helloworld_async/spec/openapi.yaml --mock=all
