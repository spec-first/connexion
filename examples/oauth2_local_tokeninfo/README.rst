===============================
OAuth2 Local Validation Example
===============================

This example demonstrates how to implement a resource server with Connexion.
The app will lookup OAuth2 Bearer tokens in a static map.

Running:

.. code-block:: bash

    $ pip install --upgrade connexion  # install Connexion from PyPI
    $ python app.py

Now open your browser and go to http://localhost:8080/openapi/ui/ to see the Swagger UI.

You can use the hardcoded tokens to request the endpoint:

.. code-block:: bash

    $ curl http://localhost:8080/openapi/secret   # missing authentication
    $ curl -H 'Authorization: Bearer 123' http://localhost:8080/openapi/secret
    $ curl -H 'Authorization: Bearer 456' http://localhost:8080/swagger/secret

