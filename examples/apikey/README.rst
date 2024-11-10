===============
API Key Example
===============

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

.. code-block:: bash

    $ python app.py

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec

The hardcoded apikey is `asdf1234567890`.

Test it out (in another terminal):

.. code-block:: bash

    $ curl -H 'X-Auth: asdf1234567890' http://localhost:8080/openapi/secret
    $ curl -H 'X-Auth: asdf1234567890' http://localhost:8080/swagger/secret
