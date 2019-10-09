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

Keep in mind that Connexion follows how `HTTP methods work in Flask`_
and therefore HEAD requests will be handled by the ``operationId`` specified
under GET in the specification. If both methods are supported,
``connexion.request.method`` can be used to determine which request was made.

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

Automatic Routing with MethodViewResolver
-------------------------------------------

``MethodViewResolver`` is an customised Resolver based on ``RestyResolver``
to take advantage of MethodView structure of building Flask APIs.
The ``MethodViewResolver`` will compose an ``operationId`` based on the path and HTTP method of
the endpoints in your specification. The path will be based on the path you provide in the app.add_api and the path provided in the URL endpoint (specified in the swagger or openapi3).

.. code-block:: python

    from connexion.resolver import MethodViewResolver

    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml', resolver=MethodViewResolver('api'))

And associated YAML

.. code-block:: yaml

   paths:
     /foo:
       get:
          # Implied operationId: api.FooView.search
       post:
          # Implied operationId: api.FooView.post

     '/foo/{id}':
       get:
          # Implied operationId: api.FooView.get
       put:
          # Implied operationId: api.FooView.put
       copy:
          # Implied operationId: api.FooView.copy
       delete:
          # Implied operationId: api.FooView.delete


The structure expects a Class to exists inside the directory ``api`` that conforms to the naming ``<<Classname with Capitalised name>>View``.
In the above yaml the necessary MethodView implementation is as follows:

.. code-block:: python

  import datetime

  from connexion import NoContent
  from flask import request
  from flask.views import MethodView


  class PetsView(MethodView):
      """ Create Pets service
      """
      method_decorators = []
      pets = {}

      def post(self):
        body= request.json
        name = body.get("name")
        tag = body.get("tag")
        count = len(self.pets)
        pet = {}
        pet['id'] = count + 1
        pet["tag"] = tag
        pet["name"] = name
        pet['last_updated'] = datetime.datetime.now()
        self.pets[pet['id']] = pet
        return pet, 201

      def put(self, petId):
        body = request.json
        name = body["name"]
        tag = body.get("tag")
        id_ = int(petId)
        pet = self.pets.get(petId, {"id": id_})
        pet["name"] = name
        pet["tag"] = tag
        pet['last_updated'] = datetime.datetime.now()
        self.pets[id_] = pet
        return self.pets[id_], 201

      def delete(self, petId):
        id_ = int(petId)
        if self.pets.get(id_) is None:
            return NoContent, 404
        del self.pets[id_]
        return NoContent, 204

      def get(self, petId):
        id_ = int(petId)
        if self.pets.get(id_) is None:
            return NoContent, 404
        return self.pets[id_]

      def search(self, limit=100):
        # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
        return list(self.pets.values())[0:limit]

and a __init__.py file to make the Class visible in the api directory.

.. code-block:: Python

  from .petsview import PetsView

``MethodViewResolver`` will give precedence to any ``operationId``
encountered in the specification. It will also respect
``x-swagger-router-controller``. You may import and extend
``connexion.resolver.MethodViewResolver`` to implement your own ``operationId``
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

Setting a base path is useful for versioned APIs. An example of
a base path would be the ``1.0`` in ``http://MYHOST/1.0/hello_world``.

If you are using OpenAPI 3.x.x, you set your base URL path in the
servers block of the specification. You can either specify a full
URL, or just a relative path.

.. code-block:: yaml

    servers:
      - url: https://MYHOST/1.0
        description: full url example
      - url: /1.0
        description: relative path example

    paths:
      ...

If you are using OpenAPI 2.0, you can define a ``basePath`` on the top level
of your OpenAPI 2.0 specification.

.. code-block:: yaml

    basePath: /1.0

    paths:
      ...

If you don't want to include the base path in your specification, you
can provide it when adding the API to your application:

.. code-block:: python

    app.add_api('my_api.yaml', base_path='/1.0')

Swagger UI path
---------------

Swagger UI is available at ``/ui/`` by default.

You can choose another path through options:

.. code-block:: python

    options = {'swagger_url': '/'}
    app = connexion.App(__name__, options=options)

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

.. _Operation Object: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _HTTP Methods work in Flask: http://flask.pocoo.org/docs/1.0/quickstart/#http-methods
