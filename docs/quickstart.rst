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
Request Handling
----------------
Connexion validates incoming requests for conformance with the schemas described in swagger specification.

Request parameters will be provided to the handler functions as keyword arguments if they are included in the function's
signature, otherwise body parameters can be accessed from ``connexion.request.json`` and query parameters can be
accessed from ``connexion.request.args``.


Response Serialization
----------------------
By default and if the specification defines that a endpoint produces only json, connexion will automatically serialize
the return value for you and set the right content type in the HTTP header.
If the endpoint produces a single non json mimetype then connexion will automatically  set the right content type in the
HTTP header.


Error Handling
--------------
By default connexion error messages are JSON serialized according to `Problem Details for HTTP APIs <http_problem_>`_.

Application can return errors using ``connexion.problem``.


Swagger JSON
------------
Connexion makes the OpenAPI/Swagger specification in JSON format
available from ``swagger.json`` in the base path of the API.

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

Likewise, you can configure the filesystem and URL paths to the Swagger UI
documentation:

.. code-block:: python

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_path='/path/to/swagger-ui', swagger_url='doc')


Server Backend
--------------
By default connexion uses the default flask server but you can also use Tornado_ as the http server, to do so set server
to ``tornado``:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, port = 8080, specification_dir='swagger/', server='tornado')


.. _http_problem: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
.. _Jinja2: http://jinja.pocoo.org/
.. _swagger.spec: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md
.. _swagger.spec.operation: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _Tornado: http://www.tornadoweb.org/en/stable/
