Routing
=======

Endpoint Routing to Your Python Views
-------------------------------------

Connexion uses the ``operationId`` from each `Operation Object`_ to
identify which Python function should handle each URL.

**Explicit Routing**:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

If you provided this path in your specification POST requests to
``http://MYHOST/hello_world``, it would be handled by the function
``hello_world`` in ``myapp.api`` module. Optionally, you can include
``x-swagger-router-controller`` in your operation definition, making
``operationId`` relative:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          x-swagger-router-controller: myapp.api
          operationId: hello_world

Automatic Routing
-----------------

To customize this behavior, Connexion can use alternative
``Resolvers``—for example, ``RestyResolver``. The ``RestyResolver``
will compose an ``operationId`` based on the path and HTTP method of
the endpoints in your specification:

.. code-block:: python

    from connexion.resolver import RestyResolver

    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml', resolver=RestyResolver('api'))

.. code-block:: yaml

   paths:
     /:
       get:
          # Implied operationId: api.get
     /foo:
       get:
          # Implied operationId: api.foo.search
       post:
          # Implied operationId: api.foo.post

     '/foo/{id}':
       get:
          # Implied operationId: api.foo.get
       put:
          # Implied operationId: api.foo.put
       copy:
          # Implied operationId: api.foo.copy
       delete:
          # Implied operationId: api.foo.delete

``RestyResolver`` will give precedence to any ``operationId``
encountered in the specification. It will also respect
``x-swagger-router-controller``. You may import and extend
``connexion.resolver.Resolver`` to implement your own ``operationId``
(and function) resolution algorithm.

Parameter Name Sanitation
-------------------------

The names of query and form parameters, as well as the name of the body
parameter are sanitized by removing characters that are not allowed in Python
symbols. I.e. all characters that are not letters, digits or the underscore are
removed, and finally characters are removed from the front until a letter or an
under-score is encountered. As an example:

.. code-block:: python

    >>> re.sub('^[^a-zA-Z_]+', '', re.sub('[^0-9a-zA-Z_]', '', '$top'))
    'top'

Without this sanitation it would e.g. be impossible to implement an
`OData
<http://www.odata.org>`_ API.

Parameter Variable Converters
-----------------------------

Connexion supports Flask's ``int``, ``float``, and ``path`` route parameter
`variable converters
<http://flask.pocoo.org/docs/0.12/quickstart/#variable-rules>`_.
Specify a route parameter's type as ``integer`` or ``number`` or its type as
``string`` and its format as ``path`` to use these converters. For example:

.. code-block:: yaml

  paths:
    /greeting/{name}:
      # ...
      parameters:
        - name: name
          in: path
          required: true
          type: string
          format: path

will create an equivalent Flask route ``/greeting/<path:name>``, allowing
requests to include forward slashes in the ``name`` url variable.

API Versioning and basePath
---------------------------

You can also define a ``basePath`` on the top level of the API
specification. This is useful for versioned APIs. To serve the
previous endpoint from ``http://MYHOST/1.0/hello_world``, type:

.. code-block:: yaml

    basePath: /1.0

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

If you don't want to include the base path in your specification, you
can just provide it when adding the API to your application:

.. code-block:: python

    app.add_api('my_api.yaml', base_path='/1.0')

Swagger JSON
------------
Connexion makes the OpenAPI/Swagger specification in JSON format
available from ``swagger.json`` in the base path of the API.

You can disable the Swagger JSON at the application level:

.. code-block:: python

    app = connexion.FlaskApp(__name__, specification_dir='swagger/',
                        swagger_json=False)
    app.add_api('my_api.yaml')

You can also disable it at the API level:

.. code-block:: python

    app = connexion.FlaskApp(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_json=False)
