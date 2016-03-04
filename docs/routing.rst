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

    app = connexion.App(__name__)
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
          # Implied operationId: api.foo.post
       copy:
          # Implied operationId: api.foo.copy
       delete:
          # Implied operationId: api.foo.delete

``RestyResolver`` will give precedence to any ``operationId``
encountered in the specification. It will also respect
``x-router-controller``. You may import and extend
``connexion.resolver.Resolver`` to implement your own ``operationId``
(and function) resolution algorithm.

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
