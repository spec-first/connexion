========================
Custom Validator Example
========================

.. warning::

    This example is outdated. Currently validation no longer adapts the body.
    TODO: decide if validation should adapt body or how we want to enable defaults otherwise.

In this example we fill-in non-provided properties with their defaults.
Validator code is based on example from `python-jsonschema docs`_.

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[swagger-ui,uvicorn]>=3.1.0'

Running
-------

Launch the connexion server with this command:

.. code-block:: bash

    $ python app.py

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec

If you send a ``POST`` request with empty body ``{}``, you should receive
echo with defaults filled-in.

.. _python-jsonschema docs: https://python-jsonschema.readthedocs.io/en/latest/faq/#why-doesn-t-my-schema-that-has-a-default-property-actually-set-the-default-on-my-instance
