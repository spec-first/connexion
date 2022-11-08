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
``hello_world`` in ``myapp.api`` module.

Optionally, you can include ``x-swagger-router-controller`` in your operation
definition, making ``operationId`` relative:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          x-swagger-router-controller: myapp.api
          operationId: hello_world

NOTE: If you are using an OpenAPI spec, you should use ``x-openapi-router-controller`` 
in your operation definition, making ``operationId`` relative:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          x-openapi-router-controller: myapp.api
          operationId: hello_world

If all your operations are relative, you can use the ``RelativeResolver`` class
instead of repeating the same ``x-swagger-router-controller`` or
``x-openapi-router-controller`` in every operation:

.. code-block:: python

    from connexion.resolver import RelativeResolver
      
    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml', resolver=RelativeResolver('api'))


Keep in mind that Connexion follows how `HTTP methods work in Flask`_
and therefore HEAD requests will be handled by the ``operationId`` specified
under GET in the specification. If both methods are supported,
``connexion.request.method`` can be used to determine which request was made.

By default, Connexion strictly enforces the presence of a handler
function for any path defined in your specification. Because of this, adding
new paths without implementing a corresponding handler function will produce
runtime errors and your application will not start. To allow new paths to be
added to your specification, e.g. in an API design first workflow, set the
``resolver_error`` to configure Connexion to provide an error response for
paths that are not yet implemented:

.. code-block:: python

    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml', resolver_error=501)

.. code-block:: yaml

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
     '/foo/{id}/bar':
       get:
          # Implied operationId: api.foo.bar.search
     '/foo/{id}/bar/{name}':
       get:
          # Implied operationId: api.foo.bar.get
          # Handler signature: `def get(id, name): ...`

``RestyResolver`` will give precedence to any ``operationId``
encountered in the specification. It will also respect
``x-swagger-router-controller`` and ``x-openapi-router-controller``.
You may import and extend ``connexion.resolver.Resolver`` to implement your own
``operationId`` (and function) resolution algorithm.
Note that when using multiple parameters in the path, they will be
collected and all passed to the endpoint handlers.

Automatic Routing with MethodViewResolver
-------------------------------------------

.. note::
   If you migrate from connexion v2 you may want to use the `MethodResolver`
   in order to maintain the old behavior. The behavior described here is the new behavior,
   introduced in connexion v3. The difference is that the `MethodResolver` works with any
   class, while the `MethodViewResolver` is specifically designed to work with flask's
   `MethodView`. Previously, in v2, the `MethodViewResolver` worked like the `MethodResolver`
   in v3. One consequence is that the `MethodResolver` will look for `search` and `get`
   methods for list and single operations respectively, while `MethodViewResolver` uses
   the `dispatch_request` method of the given class and therefore handles both, list and
   single operations via the same `get` method.  

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
    from flask.views import MethodView


    class PetsView(MethodView):
      """Create Pets service"""

      pets = {}

      def post(self, body: dict):
        name = body.get("name")
        tag = body.get("tag")
        count = len(self.pets)
        pet = {}
        pet["id"] = count + 1
        pet["tag"] = tag
        pet["name"] = name
        pet["last_updated"] = datetime.datetime.now()
        self.pets[pet["id"]] = pet
        return pet, 201

      def put(self, petId, body: dict):
        name = body["name"]
        tag = body.get("tag")
        pet = self.pets.get(petId, {"id": petId})
        pet["name"] = name
        pet["tag"] = tag
        pet["last_updated"] = datetime.datetime.now()
        self.pets[petId] = pet
        return self.pets[petId], 201

      def delete(self, petId):
        id_ = int(petId)
        if self.pets.get(id_) is None:
          return NoContent, 404
        del self.pets[id_]
        return NoContent, 204

      def get(self, petId=None, limit=100):
        if petId is None:
          # NOTE: we need to wrap it with list for Python 3 as 
          # dict_values is not JSON serializable
          return list(self.pets.values())[0:limit]
        if self.pets.get(petId) is None:
          return NoContent, 404
        return self.pets[petId]


and a __init__.py file to make the Class visible in the api directory.

.. code-block:: python

    from .petsview import PetsView


The `as_view` method of the class is called to create the view function.
Its `dispatch_request` method is used to route requests based on the HTTP method. 
Therefore it is required to use the same `get` method for both, collection and 
single resources. I.E. `/pets` and `/pets/{id}`.

It is possible to use decorators for the Method view by listing them in the 
decorator attribute of the class:

.. code-block:: python

    def example_decorator(f):

        def decorator(*args, **kwargs):
            return f(*args, **kwargs)

        return decorator

    class PetsView(MethodView):
      """Create Pets service"""

      decorators = [example_decorator]

      ...


Additionally, you may inject dependencies into the class by declaring parameters 
for this class in the `__init__` method and providing the arguments in the 
`MethodViewResolver` call. The arguments are passed down to the class when 
`as_view` is called.

A class might look like this:

.. code-block:: python
  
  class PetsView(MethodView):
    def __init__(self, pets):
      self.pets = pets


And the arguments are provided like this:

.. code-block:: python

  MethodViewResolver("api", class_arguments={"PetsView": {"kwargs": {"pets": zoo}}})


``MethodViewResolver`` will give precedence to any ``operationId``
encountered in the specification. It will also respect
``x-swagger-router-controller`` and ``x-openapi-router-controller``.
You may import and extend ``connexion.resolver.MethodViewResolver`` to implement
your own ``operationId`` (and function) resolution algorithm.

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

You can also convert *CamelCase* parameters to *snake_case* automatically using `pythonic_params` option:

.. code-block:: python

    app = connexion.FlaskApp(__name__)
    app.add_api('api.yaml', ..., pythonic_params=True)

With this option enabled, Connexion firstly converts *CamelCase* names
to *snake_case*. Secondly it looks to see if the name matches a known built-in
and if it does it appends an underscore to the name.

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

Regex Routing with Path Parameter Patterns
------------------------------------------

In addition to validating string parameters with the ``pattern`` property, Connexion can also use it to
route otherwise identical requests paths, for example:

.. code-block:: yaml

  paths:
    /greeting/{identifier}:
      # ...
      parameters:
        - name: identifier
          in: path
          required: true
          schema:
            type: string
            pattern: '[0-9a-z]{20}'
    /greeting/{short_name}:
      # ...
      parameters:
        - name: short_name
          in: path
          required: true
          schema:
            type: string
            pattern: '\w*{1,10}'
    /greeting/{long_name}:
      # ...
      parameters:
        - name: long_name
          in: path
          required: true
          schema:
            type: string

``/greeting/123abc456def789ghijk`` will route to the first endpoint.

``/greeting/Trillian`` will route to the second endpoint.

``/greeting/Tricia McMillan`` will route the the third endpoint because it has no pattern defined,
and therefore acts as a catch-all for requests that don't match any defined patterns for the same path.

NOTE: Regex values for the same path must be mutually exclusive. If not, and the regex overlaps,
the routing behavior will be undefined.

NOTE: Pattern routing in connexion v3 will slightly change the behavior of existing endpoints from connexion v2.
In connexion v2, a request that provides a parameter that does not match
the defined regex pattern will return a 400 error with a message about the pattern not matching.
In connexion v3, the same request will return a 404 error.


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
