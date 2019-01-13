=======================
HTTP Basic Auth Example
=======================

Running:

.. code-block:: bash

    $ sudo pip3 install --upgrade connexion[swagger-ui]  # install Connexion from PyPI
    $ ./app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.

The hardcoded credentials are ``admin`` and ``secret``.

For a more advanced example which reuses oauth scope for authorization see
the `OpenAPI3 Basic Auth example`_.

.. _OpenAPI3 Basic Auth example: https://github.com/zalando/connexion/tree/master/examples/openapi3/basicauth
