===================
Split Specs Example
===================

This example demonstrates split specifications and relative references.
The OpenAPI specification and the Swagger specification are stored in
multiple files and use references that are resolved by Connexion.

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash
    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[flask,swagger-ui,uvicorn]>=3.1.0'

Running
-------

Launch the connexion server with this command:

Running:

.. code-block:: bash

    $ python app.py

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec
