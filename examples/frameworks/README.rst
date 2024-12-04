==================
Framework Examples
==================

This directory contains minimal examples on how to use Connexion with different frameworks.

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[swagger-ui,uvicorn]>=3.1.0'
    $ pip install -r requirements.txt

Running
-------

Launch the connexion server with one of these commands:

.. code-block:: bash

    $ python hello_quart.py
    $ python hello_starlette.py

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec
