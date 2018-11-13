Quickstart
==========


Prerequisites
-------------

Python 2.7 or Python 3.4+

Installing It
-------------

In your command line, type this:

.. code-block:: bash

    $ pip install connexion[swagger-ui]


Running It
----------

Put your API YAML inside a folder in the root path of your application (e.g ``openapi/``) and then do

.. code-block:: python

    import connexion

    app = connexion.FlaskApp(__name__, specification_dir='openapi/')
    app.add_api('my_api.yaml')
    app.run(port=8080)


Dynamic Rendering of Your Specification
---------------------------------------

Connexion uses Jinja2_ to allow specification parameterization through
`arguments` parameter. You can either define specification arguments
globally for the application in the `connexion.App` constructor, or
for each specific API in the `connexion.App#add_api` method:

.. code-block:: python

    app = connexion.FlaskApp(__name__, specification_dir='openapi/',
                        arguments={'global': 'global_value'})
    app.add_api('my_api.yaml', arguments={'api_local': 'local_value'})
    app.run(port=8080)

When a value is provided both globally and on the API, the API value
will take precedence.

The Swagger UI Console
----------------------
The Swagger UI for an API is available, by default, in
``{base_path}/ui/`` where ``base_path`` is the base path of the API.

You can disable the Swagger UI at the application level:

.. code-block:: python

    options = {"swagger_ui": False}
    app = connexion.FlaskApp(__name__, specification_dir='openapi/',
                        options=options)
    app.add_api('my_api.yaml')


You can also disable it at the API level:

.. code-block:: python

    options = {"swagger_ui": False}
    app = connexion.FlaskApp(__name__, specification_dir='openapi/')
    app.add_api('my_api.yaml', options=options)

Server Backend
--------------
By default connexion uses the default flask server but you can also use Tornado_ or gevent_ as the HTTP server, to do so set server
to ``tornado`` or ``gevent``:

.. code-block:: python

    import connexion

    app = connexion.FlaskApp(__name__, port = 8080, specification_dir='openapi/', server='tornado')


Connexion has the ``aiohttp`` framework as server backend too:

.. code-block:: python

    import connexion

    app = connexion.AioHttpApp(__name__, port = 8080, specification_dir='openapi/')


.. _Jinja2: http://jinja.pocoo.org/
.. _Tornado: http://www.tornadoweb.org/en/stable/
.. _gevent: http://www.gevent.org/
