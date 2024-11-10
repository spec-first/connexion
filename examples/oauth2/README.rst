==============
OAuth2 Example
==============

This example demonstrates how to implement a resource server with Connexion.
The app will lookup OAuth2 Bearer tokens with the given token info function.

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

Start a mock server in the background, then launch the connexion server,
with these commands:

.. code-block:: bash

    $ python mock_tokeninfo.py &       # start mock in background
    $ python app.py

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec

You can use the hardcoded tokens to request the endpoint:

.. code-block:: bash

    $ curl http://localhost:8080/openapi/secret   # missing authentication
    $ curl -H 'Authorization: Bearer 123' http://localhost:8080/openapi/secret
    $ curl -H 'Authorization: Bearer 456' http://localhost:8080/swagger/secret

