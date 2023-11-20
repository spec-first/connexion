Request handling
================

When your application receives a request, Connexion provides a lot of functionality based on your
OpenAPI spec:

- It checks the security (see :doc:`security`)
- It routes the request to the correct endpoint (see :doc:`routing`)
- It validates the body and parameters (see :doc:`validation`)
- It parses and passes the body and parameters to your python function

On this page, we zoom in on the final part.

Automatic parameter handling
----------------------------

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        Connexion automatically maps the parameters defined in your endpoint specification to the
        arguments defined your associated Python function, parsing and casting values when
        possible. All you need to do, is make sure the arguments of your function match the
        parameters in your specification.

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        Connexion automatically maps the parameters defined in your endpoint specification to the
        arguments defined your associated Python function, parsing and casting values when
        possible. All you need to do, is make sure the arguments of your function match the
        parameters in your specification.

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        Connexion can automatically map the parameters defined in your endpoint specification to
        the arguments defined your associated Python function, parsing and casting values when
        possible. All you need to do, is make sure the arguments of your function match the
        parameters in your specification.

        To activate this behavior when using the ``ConnexionMiddleware`` wrapping a third party
        application, you can leverage the following decorators provided by Connexion:

        * ``WSGIDecorator``: provides automatic parameter injection for WSGI applications. Note
          that this decorator injects Werkzeug / Flask datastructures.

        * ``FlaskDecorator``: provides automatic parameter injection and response serialization for
          Flask applications.

        * ``ASGIDecorator``: provides automatic parameter injection for ASGI applications. Note that
          this decorator injects Starlette datastructures (such as UploadFile).

        * ``StarletteDecorator``: provides automatic parameter injection and response serialization
          for Starlette applications.

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware
            from connexion.decorators import ASGIDecorator

            @app.route("/greeting/<name>", methods=["POST"])
            @ASGIDecorator()
            def post_greeting(name):
                ...

            app = App(__name__)
            app = ConnexionMiddleware(app)
            app.add_api("openapi.yaml")

        For a full example, see our `Frameworks`_ example.

For example, if you have an endpoint specified as:

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        .. code-block:: yaml
            :caption: **openapi.yaml**

            paths:
              /foo:
                get:
                  operationId: api.foo_get
                  parameters:
                    - name: message
                      description: Some message.
                      in: query
                      schema:
                        type: string
                      required: true

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        .. code-block:: yaml
            :caption: **swagger.yaml**

            paths:
              /foo:
                get:
                  operationId: api.foo_get
                  parameters:
                    - name: message
                      description: Some message.
                      in: query
                      type: string
                      required: true

And the view function as:

.. code-block:: python
    :caption: **api.py**

    def foo_get(message):
        ...

Connexion will automatically identify that your view function expects an argument named ``message``
and will pass in the value of the endpoint parameter ``message``.

This works for both path and query parameters.

Body
----

The body will also be passed to your function.

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        In the OpenAPI 3 spec, the ``requestBody`` does not have a name. By default it will be
        passed into your function as ``body``. You can use ``x-body-name`` in your operation to
        override this name.

        .. code-block:: yaml
            :caption: **openapi.yaml**

            paths:
              /foo:
                post:
                  operationId: api.foo_get
                  requestBody:
                    x-body-name: payload
                    content:
                      application/json:
                        schema:
                          ...

        .. code-block:: python
            :caption: **api.py**

            # Default
            def foo_get(body)
                ...

            # Based on x-body-name
            def foo_get(payload)
                ...

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        In the Swagger 2 specification, you can define the name of your body. Connexion will pass
        the body to your function using this name.

        .. code-block:: yaml
            :caption: **swagger.yaml**

            paths:
              /foo:
                post:
                  consumes:
                    - application/json
                    parameters:
                      - in: body
                        name: payload
                        schema:
                          ...

        .. code-block:: python
            :caption: **api.py**

            def foo_get(payload)
                ...

        Form data
        `````````

        In Swagger 2, form data is defined as parameters in your specification, and Connexion
        passes these parameters individually:


        .. code-block:: yaml
            :caption: **swagger.yaml**

            paths:
              /foo:
                post:
                  operationId: api.foo_get
                  consumes:
                    - application/json
                  parameters:
                    - in: formData
                      name: field1
                      type: string
                    - in: formData
                      name: field2
                      type: string

        .. code-block:: python
            :caption: **api.py**

            def foo_get(field1, field2)
                ...

Connexion will not automatically pass in the default values defined in your ``requestBody``
definition, but you can activate this by configuring a different
:ref:`RequestBodyValidator<validation:Custom validators>`.

Files
-----

Connexion extracts the files from the body and passes them into your view function separately:

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        .. code-block:: yaml
            :caption: **openapi.yaml**

            paths:
              /foo:
                post:
                  operationId: api.foo_get
                  requestBody:
                    content:
                      multipart/form-data:
                        schema:
                          type: object
                          properties:
                            file:
                              type: string
                              format: binary

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        In the Swagger 2 specification, you can define the name of your body. Connexion will pass
        the body to your function using this name.

        .. code-block:: yaml
            :caption: **swagger.yaml**

            paths:
              /foo:
                post:
                  consumes:
                    - application/json
                  parameters:
                    - name: file
                      type: file
                      in: formData


.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        If you're using the `AsyncApp`, the files are provided as `Starlette.UploadFile`_ instances.

        .. code-block:: python
            :caption: **api.py**

                    def foo_get(file)
                        assert isinstance(file, starlette.UploadFile)
                        ...


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        If you're using the `FlaskApp`, the files are provided as `werkzeug.FileStorage`_ instances.

        .. code-block:: python
            :caption: **api.py**

                    def foo_get(file)
                        assert isinstance(file, werkzeug.FileStorage)
                        ...

When your specification defines an array of files:

.. code-block:: yaml

    type: array
    items:
        type: string
        format: binary

They will be provided to your view function as a list.

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **api.py**

                    def foo_get(file)
                        assert isinstance(file, list)
                        assert isinstance(file[0], starlette.UploadFile)
                        ...


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **api.py**

                    def foo_get(file)
                        assert isinstance(file, list)
                        assert isinstance(file[0], werkzeug.FileStorage)
                        ...

.. _Starlette.UploadFile: https://www.starlette.io/requests/#request-files
.. _werkzeug.FileStorage: https://werkzeug.palletsprojects.com/en/3.0.x/datastructures/#werkzeug.datastructures.FileStorage

Optional arguments & Defaults
-----------------------------

If a default value is defined for a parameter in the OpenAPI specification, Connexion will
automatically pass it in if no value was included in the request. If a default is defined in the
specification, you should not define a default in your Python function, as it will never be
triggered.

If an endpoint parameter is optional and no default is defined in the specification, you should
make sure the corresponding argument is optional in your Python function as well, by assigning a
default value:

.. code-block:: python
    :caption: **api.py**

    def foo_get(optional_argument=None)
        ...

Missing arguments and kwargs
----------------------------

Connexion will inspect your function signature and only pass in the arguments that it defines. If
an argument is defined in your specification, but not in your function, Connexion will ignore it.

If you do define a ``**kwargs`` argument in your function signature, Connexion will pass in all
arguments, and the ones not explicitly defined in your signature will be collected in the
``kwargs`` argument.

Parameter Name Sanitation
-------------------------

The names of query and form parameters, as well as the name of the body
parameter are sanitized by removing characters that are not allowed in Python
symbols. I.e. all characters that are not letters, digits or the underscore are
removed, and finally characters are removed from the front until a letter or an
underscore is encountered. As an example:

.. code-block:: python

    >>> re.sub('^[^a-zA-Z_]+', '', re.sub('[^0-9a-zA-Z_]', '', '$top'))
    'top'


Pythonic parameters
-------------------

You can activate Pythonic parameters by setting the ``pythonic_params`` option to ``True`` on
either the application or the API:

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import AsyncApp

            app = AsyncApp(__name__, pythonic_params=True)
            app.add_api("openapi.yaml", pythonic_params=True)


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import FlaskApp

            app = FlaskApp(__name__, pythonic_params=True)
            app.add_api("openapi.yaml", pythonic_params=True):

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app, pythonic_params=True)
            app.add_api("openapi.yaml", pythonic_params=True)

This does two things:

* *CamelCase* arguments are converted to *snake_case*
* If the argument name matches a Python builtin, an underscore is appended.

When ``pythonic_params`` is activated, the following specification:

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        .. code-block:: yaml
            :caption: **openapi.yaml**

            paths:
              /foo:
                get:
                  operationId: api.foo_get
                  parameters:
                    - name: filter
                      description: Some filter.
                      in: query
                      schema:
                        type: string
                      required: true
                    - name: FilterOption
                      description: Some filter option.
                      in: query
                      schema:
                        type: string

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        .. code-block:: yaml
            :caption: **swagger.yaml**

            paths:
              /foo:
                get:
                  operationId: api.foo_get
                  parameters:
                    - name: filter
                      description: Some filter.
                      in: query
                      type: string
                      required: true
                    - name: FilterOption
                      description: Some filter option.
                      in: query
                      type: string

Maps to the following Python function:

.. code-block:: python
    :caption: **api.py**

    def foo_get(filter_, filter_option=None):
        ...

Type casting
------------

Whenever possible Connexion will try to parse your argument values and cast them to the correct
Python type:

+--------------+-------------+
| OpenAPI Type | Python Type |
|              |             |
+==============+=============+
| integer      | int         |
+--------------+-------------+
| string       | str         |
+--------------+-------------+
| number       | float       |
+--------------+-------------+
| boolean      | bool        |
+--------------+-------------+
| array        | list        |
+--------------+-------------+
| object       | dict        |
+--------------+-------------+
| null         | None        |
+--------------+-------------+

Parameter serialization
-----------------------

Array and object parameters need to be serialized into lists and dicts.

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        The `OpenAPI 3 specification`_ defines the `style` and `explode` keywords which specify how
        these parameters should be serialized.

        To handle these, Connexion provides the ``OpenAPIUriParser`` class, which is enabled by
        default when using an OpenAPI 3 spec.

        Not all combinations of `style` and `explode` are supported yet. Please open an `issue`_ if
        you run into any problems.

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        The `Swagger 2 specification`_ defines the `collectionFormat` keyword to specify how
        these parameters should be serialized.

        To handle this for you, Connexion provides the ``Swagger2URIParser`` class, which is
        enabled by default when using a Swagger 2 spec. It currently supports the `pipes`, `csv`,
        and `multi` collection formats.

        This parser adheres to the Swagger 2.0 spec, and will only join together multiple instance
        of the same query parameter if the collectionFormat is set to `multi`. Query parameters
        are parsed from left to right, so if a query parameter is defined twice, then the
        right-most definition wins. For example, if you provided a URI with the query string
        ``?letters=a,b,c&letters=d,e,f`` and ``collectionFormat: csv``, then connexion will set
        ``letters = ['d', 'e', 'f']``.

        Connexion also provides two alternative parsers:

        * The ``FirstValueURIParser``, which behaves like the ``Swagger2URIParser``, except that it
          prefers the first defined value.
        * The ``AlwaysMultiURIParser``, which behaves like the ``Swagger2URIParser``, except that
          it always joins together multiple instances of the same query parameter.

Context
-------

Connexion can pass in some additional context. By default, this contains the following information:

.. code-block:: python

    {
        "api_base_path": ...  # The base path of the matched API
        "operation_id": ...  # The operation id of matched operation
        "user": ...  # User information from authentication
        "token_info": ...  # Token information from authentication
    }

Third party or custom middleware might add additional fields to this.

To receive this in your function, you can either:

* Specify the ``context_`` argument in your function signature, and the context dict will be
  passed in as a whole:

  .. code-block:: python
    :caption: **api.py**

    def foo_get(context_):
        ...

* Specify the keys individually in your function signature:

  .. code-block:: python
    :caption: **api.py**

    def foo_get(user, token_info):
        ...

Request object
--------------

Connexion also exposes a ``Request`` class which holds all the information about the incoming
request.

.. code-block:: python

    from connexion import request

.. dropdown:: View a detailed reference of the ``connexion.request`` class
    :icon: eye

    .. warning::

        The asynchronous body arguments (body, form, files) might already be consumed by connexion.
        We recommend to let Connexion inject them into your view function as mentioned above.

    .. autoclass:: connexion.lifecycle.ConnexionRequest
       :members:
       :undoc-members:
       :inherited-members:

.. _Frameworks: https://github.com/spec-first/connexion/tree/main/examples/frameworks
.. _OpenAPI 3 specification: https://swagger.io/docs/specification/serialization
.. _Swagger 2 specification: https://swagger.io/docs/specification/2-0/describing-parameters/#array
.. _issue: https://github.com/spec-first/connexion/issues
