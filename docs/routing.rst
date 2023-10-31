Routing
=======

Connexion leverages your OpenAPI contract to route requests to your python functions. This can
be done in two ways:

* `Explicitly <#explicit-routing>`_
* `Automatically <#automatic-routing>`_

Explicit routing
----------------

Connexion uses the :code:`operation_id` to link each `operation`_ in your API contract to
the python function that should handle it.

.. code-block:: python
    :caption: **openapi.yaml**

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

Based on the :code:`operationId` above, any :code:`POST` request to
:code:`http://{HOST}/hello_world`, will be handled by the :code:`hello_world` function in the
:code:`myapp.api` module.

Optionally, you can include :code:`x-openapi-router-controller` or
:code:`x-swagger-router-controller` in your :code:`operationId` to make your `operationId` relative:

.. code-block:: python
    :caption: **openapi.yaml**

    paths:
      /hello_world:
        post:
          x-openapi-router-controller: myapp.api
          operationId: hello_world


If all your operations are relative, you can use the :code:`RelativeResolver` class when
registering your API instead of repeating the same :code:`x-openapi-router-controller` in every
operation:

.. code-block:: python
    :caption: **app.py**

    import connexion
    from connexion.resolver import RelativeResolver

    app = connexion.AsyncApp(__name__)
    app.add_api('openapi.yaml', resolver=RelativeResolver('myapp.api'))


.. dropdown:: View a detailed reference of the :code:`RelativeResolver` class
    :icon: eye

    .. autoclass:: connexion.resolver.RelativeResolver

Note that :code:`HEAD` requests will be handled by the :code:`operationId` specified under the
:code:`GET` operation in the specification. :code:`Connexion.request.method` can be used to
determine which request was made. See :class:`.ConnexionRequest`.

Automatic routing
-----------------

Connexion can also automate the routing for you. You can choose from different :code:`Resolvers`
implementing different resolution strategies.

RestyResolver
`````````````

The :code:`RestyResolver` will infer an :code:`operationId` based on the path and HTTP method of
each operation in your specification:

.. code-block:: python
    :caption: **app.py**

    import connexion
    from connexion.resolver import RestyResolver

    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml', resolver=RestyResolver('api'))

.. code-block:: yaml
    :caption: **openapi.yaml**

    paths:
      /:
        get:
           # Implied operationId: api.get
      /foo:
        get:
           # Implied operationId: api.foo.search
        post:
           # Implied operationId: api.foo.post
      /foo/{id}:
        get:
           # Implied operationId: api.foo.get
        put:
           # Implied operationId: api.foo.put
        copy:
           # Implied operationId: api.foo.copy
        delete:
           # Implied operationId: api.foo.delete
      /foo/{id}/bar:
        get:
           # Implied operationId: api.foo.bar.search
      /foo/{id}/bar/{name}:
        get:
           # Implied operationId: api.foo.bar.get

``RestyResolver`` will give precedence to any ``operationId`` encountered in the specification and
respects ``x-openapi-router-controller`` and ``x-swagger-router-controller``.

.. dropdown:: View a detailed reference of the :code:`RestyResolver` class
    :icon: eye

    .. autoclass:: connexion.resolver.RestyResolver

MethodResolver
``````````````

The ``MethodResolver`` works like a ``RestyResolver``, but routes to class methods instead of
functions.

.. code-block:: python
    :caption: **app.py**

    import connexion
    from connexion.resolver import MethodResolver

    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml', resolver=MethodResolver('api'))


.. code-block:: yaml
    :caption: **openapi.yaml**

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


The structure expects a Class to exists inside the ``api`` module with the name
``<<CapitalisedPath>>View``.

.. code-block:: python
    :caption: **api.py**

    class PetsView:

      def post(self, body: dict):
        ...

      def put(self, petId, body: dict):
        ...

      def delete(self, petId):
        ...

      def get(self, petId=None):
        ...

      def search(limit=100):
        ...

It is possible to use decorators for the Method view by listing them in the
decorator attribute of the class:

.. code-block:: python
    :caption: **api.py**

    def example_decorator(f):

        def decorator(*args, **kwargs):
            return f(*args, **kwargs)

        return decorator

    class PetsView:
      """Create Pets service"""

      decorators = [example_decorator]

      ...


Additionally, you may inject dependencies into the class by declaring parameters
for this class in the ``__init__`` method and providing the arguments in the
``MethodViewResolver()`` call. The arguments are passed down to the class when
``as_view`` is called.

A class might look like this:

.. code-block:: python
    :caption: **api.py**

    class PetsView:
        def __init__(self, pets):
            self.pets = pets


And the arguments are provided like this:

.. code-block:: python
    :caption: **app.py**

    MethodViewResolver("api", class_arguments={"PetsView": {"kwargs": {"pets": zoo}}})

``MethodResolver`` will give precedence to any ``operationId`` encountered in the specification and
respects ``x-openapi-router-controller`` and ``x-swagger-router-controller``.

.. dropdown:: View a detailed reference of the :code:`MethodResolver` class
    :icon: eye

    .. autoclass:: connexion.resolver.MethodResolver

MethodViewResolver
``````````````````

The ``MethodResolver`` works like a ``MethodViewResolver``, but routes to class methods of a
Flask ``MethodView`` subclass.

.. note::
    If you migrate from connexion v2 you may want to use the ``MethodResolver`` in order to maintain
    the old behavior. The behavior described here is the new behavior, introduced in connexion v3.
    Previously, in v2, the ``MethodViewResolver`` worked like the ``MethodResolver`` in v3.

Another difference is that the ``MethodResolver`` will look for ``search`` and ``get``
methods for `collection` and `single item` operations respectively, while ``MethodViewResolver``
handles both `collection` and `single item` operations via the same ``get`` method.

.. code-block:: python
    :caption: **app.py**

    import connexion
    from connexion.resolver import MethodResolver

    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml', resolver=MethodViewResolver('api'))


.. code-block:: yaml
    :caption: **openapi.yaml**

    paths:
      /foo:
      get:
        # Implied operationId: api.FooView.get
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


The structure expects a Class to exists inside the ``api`` module with the name
``<<CapitalisedPath>>View``.

.. code-block:: python
    :caption: **api.py**

    from flask.views import MethodView


    class PetsView(MethodView):

      def post(self, body: dict):
        ...

      def put(self, petId, body: dict):
        ...

      def delete(self, petId):
        ...

      def get(self, petId=None, limit=100):
        ...

.. dropdown:: View a detailed reference of the :code:`MethodViewResolver` class
    :icon: eye

    .. autoclass:: connexion.resolver.MethodViewResolver

Custom resolver
```````````````

You can import and extend ``connexion.resolver.Resolver`` to implement your own
``operationId`` and function resolution algorithm.

.. dropdown:: View a detailed reference of the :code:`RestyResolver` class
    :icon: eye

    .. autoclass:: connexion.resolver.Resolver
        :members:

.. note::

    If you implement a custom ``Resolver``, and think it would be valuable for other users, we
    would appreciate it as a contribution.


Resolver error
--------------

By default, Connexion strictly enforces the presence of a handler
function for any path defined in your specification. Because of this, adding
new paths without implementing a corresponding handler function will produce
runtime errors and your application will not start. To allow new paths to be
added to your specification, e.g. in an API design first workflow, set the
``resolver_error`` to configure Connexion to provide an error response for
paths that are not yet implemented:

.. code-block:: python
    :caption: **app.py**

    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml', resolver_error=501)


Path parameters
---------------

`Path parameters`_ are variable parts of a URL path denoted with curly braces ``{ }`` in the
specification.

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        .. code-block:: yaml
            :caption: **openapi.yaml**

            paths:
              /users/{id}:
                parameters:
                  - in: path
                    name: id   # Note the name is the same as in the path
                    required: true
                    schema:
                      type: integer
                    description: The user ID

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        .. code-block:: yaml
            :caption: **swagger.yaml**

            paths:
              /users/{id}:
                parameters:
                  - in: path
                    name: id   # Note the name is the same as in the path
                    required: true
                    type: integer
                    description: The user ID.

By default this will capture characters up to the end of the path or the next `/`.

You can use convertors to modify what is captured. The available convertors are:

* `str` returns a string, and is the default.
* `int` returns a Python integer.
* `float` returns a Python float.
* `path` returns the rest of the path, including any additional `/` characters.

Convertors are used by defining them as the ``format`` in the parameter specification

Specify a route parameter's type as ``integer`` or ``number`` or its type as
``string`` and its format as ``path`` to use these converters.

Path parameters are passed as :ref:`arguments <request:Automatic parameter handling>` to your
python function.

Individual paths
----------------

You can also add individual paths to your application which are not described in your API
contract. This can be useful for eg. ``/healthz`` or similar endpoints.

.. code-block:: python
    :caption: **api.py**

    @app.route("/healthz")
    def healthz():
        return 200

    # Or as alternative to the decorator
    app.add_url_rule("/healthz", "healthz", healthz)

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. dropdown:: View a detailed reference of the ``route`` and ``add_url_rule`` methods
            :icon: eye

            .. automethod:: connexion.AsyncApp.route
                :noindex:
            .. automethod:: connexion.AsyncApp.add_url_rule
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. dropdown:: View a detailed reference of the ``route`` and ``add_url_rule`` methods
            :icon: eye

            .. automethod:: connexion.FlaskApp.route
                :noindex:
            .. automethod:: connexion.FlaskApp.add_url_rule
                :noindex:

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        When using the ``ConnexionMiddleware`` around an ASGI or WSGI application, you can
        register individual routes on the wrapped application.


API Versioning and basePath
---------------------------

Setting a base path is useful for versioned APIs. An example of
a base path would be the ``1.0`` in ``http://{HOST}/1.0/hello_world``.


.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        If you are using OpenAPI 3, you set your base URL path in the
        servers block of the specification. You can either specify a full
        URL, or just a relative path.

        .. code-block:: yaml
            :caption: **openapi.yaml**

            servers:
              - url: https://{{HOST}}/1.0
                description: full url example
              - url: /1.0
                description: relative path example

            paths:
              ...

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        If you are using Swagger 2.0, you can define a ``basePath`` on the top level
        of your Swagger 2.0 specification.

        .. code-block:: yaml
            :caption: **swagger.yaml**

            basePath: /1.0

            paths:
              ...

If you don't want to include the base path in your specification, you
can provide it when adding the API to your application:

.. code-block:: python
    :caption: **app.py**

    app.add_api('openapi.yaml', base_path='/1.0')

.. _operation: https://swagger.io/docs/specification/paths-and-operations/#operations
.. _Path parameters: https://swagger.io/docs/specification/describing-parameters/#path-parameters
