=======================
API Key Example
=======================

Running:

.. code-block:: bash

    $ pip install --upgrade connexion[swagger-ui]  # install Connexion from PyPI
    $ python app.py

Now open your browser and go to http://localhost:8080/openapi/ui/ or
http://localhost:8080/swagger/ui/ to see the Swagger UI.

The hardcoded apikey is `asdf1234567890`.

Test it out (in another terminal):

.. code-block:: bash

    $ curl -H 'X-Auth: asdf1234567890' http://localhost:8080/openapi/secret
    $ curl -H 'X-Auth: asdf1234567890' http://localhost:8080/swagger/secret
