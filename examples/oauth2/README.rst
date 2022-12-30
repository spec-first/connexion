==============
OAuth2 Example
==============

This example demonstrates how to implement a resource server with Connexion.
The app will lookup OAuth2 Bearer tokens with the given token info function.

Running:

.. code-block:: bash

    $ pip install --upgrade connexion  # install Connexion from PyPI
    $ python mock_tokeninfo.py &       # start mock in background
    $ python app.py

Now open your browser and go to http://localhost:8080/openapi/ui/ to see the Swagger UI.

You can use the hardcoded tokens to request the endpoint:

.. code-block:: bash

    $ curl http://localhost:8080/openapi/secret   # missing authentication
    $ curl -H 'Authorization: Bearer 123' http://localhost:8080/openapi/secret
    $ curl -H 'Authorization: Bearer 456' http://localhost:8080/swagger/secret

