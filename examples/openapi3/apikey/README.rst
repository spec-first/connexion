=======================
API Key Example
=======================

Running:

.. code-block:: bash

    $ sudo pip3 install --upgrade especifico[swagger-ui]  # install especifico from PyPI
    $ ./app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.

The hardcoded apikey is `asdf1234567890`.

Test it out (in another terminal):

.. code-block:: bash

    $ curl -H 'X-Auth: asdf1234567890' http://localhost:8080/secret
