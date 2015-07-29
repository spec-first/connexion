Quickstart
==========

How to use
----------

Put your API YAML inside a folder in the root path of your application (e.g ``swagger\``) and then do

.. code-block:: python

    import connexion

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/')
    app.add_api('my_api.yaml')
    app.run()


Parametrization
---------------
Connexion uses Jinja2_ to allow the parametrization of specifications.

The specification arguments can be defined globally for the application or for each specific api:

.. code-block:: python

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/', arguments={'global': 'global_value'})
    app.add_api('my_api.yaml', arguments={'api_local', 'local_value'})
    app.run()

If a value is provided both globally and on the api then the api value will take precedence.


Routing
-------
Connexion uses the ``OperationId`` from each `Operation Object <swagger.spec.operation_>`_  to identify which function
should handle each url.

For example:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

If you provided this path in your specification POST requests to ``http://MYHOST/hello_world`` would be handled by the
function ``hello_world`` in ``myapp.api``.

Additionally you can also define a ``basePath`` on the top level of the API specification, which is useful for versioned
APIs. If you wanted to serve the previous endpoint from  ``http://MYHOST/1.0/hello_world`` you could do:

.. code-block:: yaml

    basePath: /1.0

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

Other alternative if you don't want to include the base path in your specification is provide the base path when adding
the API to your application:

.. code-block:: python

    app.add_api('my_api.yaml', base_path='/1.0')


Response Serialization
----------------------
If the specification defines that a endpoint returns json connexion will automatically serialize the return value for
you and set the right content type in the HTTP header.


Error Handling
--------------
By default connexion error messages are JSON serialized according to `Problem Details for HTTP APIs <http_problem_>`_.

Application can return error using ``connexion.problem``.

Swagger Json
------------
Connexion makes the Swagger specification in json format available from ``swagger.json`` in the base path of the api.


Swagger UI
----------
The Swagger UI for an API is available, by default, in ``{base_path}/ui/`` where ``base_path`` is the base path of the
api.

You can disable the swagger ui either at application level:

.. code-block:: python

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/', swagger_ui=False)
    app.add_api('my_api.yaml')


You can also disable it at api level:

.. code-block:: python

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_ui=False)


Server Backend
--------------
By default connexion uses the default flask server.But you can also use Tornado_ or Gevent_ as the http server, to use
one them just specify it, in lowercase, with the server argument:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/', server='tornado')


.. _http_problem: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
.. _Gevent: http://www.gevent.org/
.. _Jinja2: http://jinja.pocoo.org/
.. _swagger.spec: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md
.. _swagger.spec.operation: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _Tornado: http://www.tornadoweb.org/en/stable/