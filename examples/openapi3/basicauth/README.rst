=======================
HTTP Basic Auth Example
=======================

Running:

.. code-block:: bash

    $ sudo pip3 install --upgrade connexion[swagger-ui]  # install Connexion from PyPI
    $ ./app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.

The hardcoded credentials are ``admin`` and ``secret``. For an example with
correct authentication but missing access rights, use ``foo`` and ``bar``.

For a more simple example which doesn't use oauth scope for authorization see
the `Swagger2 Basic Auth example`_.

.. _Swagger2 Basic Auth example: https://github.com/zalando/connexion/tree/master/examples/swagger2/basicauth
