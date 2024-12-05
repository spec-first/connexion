==================
SQLAlchemy Example
==================

.. note::

A simple example of how one might use SQLAlchemy as a backing store for a 
Connexion based application.

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[flask,swagger-ui,uvicorn]>=3.1.0'
    $ pip install -r requirements.txt

Running
-------

Launch the connexion server with this command:

.. code-block:: bash

    $ python app.py

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec
