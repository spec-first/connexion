Quickstart
==========


Prerequisites
-------------

Python 2.7 or Python 3.4+

Installing It
-------------

In your command line, type this:

.. code-block:: bash

    $ pip install connexion


Running It
----------

Put your API YAML inside a folder in the root path of your application (e.g ``swagger\``) and then do

.. code-block:: python

    import connexion

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml')
    app.run(port=8080)


Dynamic Rendering of Your Specification
---------------------------------------

Connexion uses Jinja2_ to allow specification parameterization through
`arguments` parameter. You can either define specification arguments
globally for the application in the `connexion.App` constructor, or
for each specific API in the `connexion.App#add_api` method:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/',
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

    app = connexion.App(__name__, specification_dir='swagger/',
                        swagger_ui=False)
    app.add_api('my_api.yaml')


You can also disable it at the API level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_ui=False)

Server Backend
--------------
By default connexion uses the default flask server but you can also use Tornado_ or gevent_ as the HTTP server, to do so set server
to ``tornado`` or ``gevent``:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/', server='tornado')


.. _Jinja2: http://jinja.pocoo.org/
.. _swagger.spec: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md
.. _swagger.spec.operation: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _Tornado: http://www.tornadoweb.org/en/stable/
.. _gevent: http://www.gevent.org/
