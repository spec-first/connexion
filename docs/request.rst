Request Handling
================
Connexion validates incoming requests for conformance with the schemas
described in swagger specification.

Request parameters will be provided to the handler functions as keyword
arguments if they are included in the function's signature, otherwise body
parameters can be accessed from ``connexion.request.json`` and query parameters
can be accessed from ``connexion.request.args``.

Request Validation
------------------
Both the request body and parameters are validated against the specification,
using `jsonschema`_.

If the request doesn't match the specification connexion will return a 400
error.

Automatic Parameter Handling
----------------------------
Connexion automatically maps the parameters defined in your endpoint
specification to arguments of your Python views as named parameters
and with value casting whenever possible. All you need to do is define
the endpoint's parameters with matching names with your views arguments.

As example you have an endpoint specified as:

.. code-block:: yaml

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

And the view function:

.. code-block:: python

    # api.py file

    def foo_get(message):
        # do something
        return 'You send the message: {}'.format(message), 200

In this example Connexion will automatically identify that your view
function expects an argument named `message` and will assign the value
of the endpoint parameter `message` to your view function.

Connexion will also use default values if they are provided.

.. note:: In the OpenAPI 3.x.x spec, the requestBody does not have a name.
          By default it will be passed in as 'body'. You can optionally
          provide the x-body-name parameter in your requestBody schema
          to override the name of the parameter that will be passed to your
          handler function.

.. warning:: Please note that when you have a parameter defined as
             *not* required at your endpoint and your Python view have
             a non-named argument, when you call this endpoint WITHOUT
             the parameter you will get an exception of missing
             positional argument.

Type casting
^^^^^^^^^^^^
Whenever possible Connexion will try to parse your argument values and
do type casting to related Python natives values. The current
available type castings are:

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
| null         | None        |
+--------------+-------------+
| object       | dict        |
+--------------+-------------+

In the OpenAPI 2.0 specification, if the `array` type is used you can define the
`collectionFormat` used to deserialize the input. Connexion currently
supports collection formats "pipes" and "csv". The default format is "csv".

.. note:: For more details about `collectionFormat`s please check the
          official `OpenAPI 2.0 Specification`_.


In the `OpenAPI 2.0 Specification`_ if you use the ``array`` type,
you can define the ``collectionFormat`` do set the deserialization behavior.
Connexion currently supports "pipes" and "csv" as collection formats.
The default format is "csv".

Connexion is opinionated about how the URI is parsed for ``array`` types.
The default behavior for query parameters that have been defined multiple
times is to join them all together. For example, if you provide a URI with
the the query string ``?letters=a,b,c&letters=d,e,f``, connexion will set
``letters = ['a', 'b', 'c', 'd', 'e', 'f']``.

You can override this behavior by specifying the URI parser in the app or
api options.

.. code-block:: python

   from connexion.decorators.uri_parsing import Swagger2URIParser
   options = {'uri_parsing_class': Swagger2URIParser}
   app = connexion.App(__name__, specification_dir='swagger/', options=options)

You can implement your own URI parsing behavior by inheriting from
``connextion.decorators.uri_parsing.AbstractURIParser``.

There are a handful of URI parsers included with connection.

+----------------------+---------------------------------------------------------------------------+
| OpenAPIURIParser     | This parser adheres to the OpenAPI 3.x.x spec, and uses the ``style``     |
| default: OpenAPI 3.0 | parameter. Query parameters are parsed from left to right, so if a query  |
|                      | parameter is defined twice, then the right-most definition will take      |
|                      | precedence. For example, if you provided a URI with the query string      |
|                      | ``?letters=a,b,c&letters=d,e,f``, and ``style: simple``, then connexion   |
|                      | will set ``letters = ['d', 'e', 'f']``. For additional information see    |
|                      | `OpenAPI 3.0 Style Values`_.                                              |
+----------------------+---------------------------------------------------------------------------+
| Swagger2URIParser    | This parser adheres to the Swagger 2.0 spec, and will only join together  |
| default: OpenAPI 2.0 | multiple instance of the same query parameter if the ``collectionFormat`` |
|                      | is set to ``multi``. Query parameters are parsed from left to right, so   |
|                      | if a query parameter is defined twice, then the right-most definition     |
|                      | wins. For example, if you provided a URI with the query string            |
|                      | ``?letters=a,b,c&letters=d,e,f``, and ``collectionFormat: csv``, then     |
|                      | connexion will set ``letters = ['d', 'e', 'f']``                          |
+----------------------+---------------------------------------------------------------------------+
| FirstValueURIParser  | This parser behaves like the Swagger2URIParser, except that it prefers    |
|                      | the first defined value. For example, if you provided a URI with the query|
|                      | string ``?letters=a,b,c&letters=d,e,f`` and ``collectionFormat: csv``     |
|                      | hen connexion will set ``letters = ['a', 'b', 'c']``                      |
+----------------------+---------------------------------------------------------------------------+
| AlwaysMultiURIParser | This parser is backwards compatible with Connexion 1.x. It joins together |
|                      | multiple instances of the same query parameter.                           |
+----------------------+---------------------------------------------------------------------------+


.. _jsonschema: https://pypi.python.org/pypi/jsonschema
.. _`OpenAPI 2.0 Specification`: https://github.com/OAI/OpenAPI-Specification/blob/OpenAPI.next/versions/2.0.md#fixed-fields-7

Parameter validation
^^^^^^^^^^^^^^^^^^^^

Connexion can apply strict parameter validation for query and form data
parameters.  When this is enabled, requests that include parameters not defined
in the swagger spec return a 400 error.  You can enable it when adding the API
to your application:

.. code-block:: python

    app.add_api('my_apy.yaml', strict_validation=True)


Nullable parameters
^^^^^^^^^^^^^^^^^^^

Sometimes your API should explicitly accept `nullable parameters`_. However
OpenAPI specification currently does `not support`_ officially a way to serve
this use case, Connexion adds the `x-nullable` vendor extension to parameter
definitions. Its usage would be:

.. code-block:: yaml

    /countries/cities:
       parameters:
         - name: name
           in: query
           type: string
           x-nullable: true
           required: true

It is supported by Connexion in all parameter types: `body`, `query`,
`formData`, and `path`. Nullable values are the strings `null` and `None`.

.. warning:: Be careful on nullable parameters for sensitive data where the
             strings "null" or "None" can be `valid values`_.

.. note:: This extension will be removed as soon as OpenAPI/Swagger
          Specification provide an official way of supporting nullable
          values.

.. _`nullable parameters`: https://github.com/zalando/connexion/issues/182
.. _`not support`: https://github.com/OAI/OpenAPI-Specification/issues/229
.. _`valid values`: http://www.bbc.com/future/story/20160325-the-names-that-break-computer-systems

Header Parameters
-----------------

Currently, header parameters are not passed to the handler functions as parameters. But they can be accessed through the underlying
``connexion.request.headers`` object which aliases the ``flask.request.headers`` object.

.. code-block:: python

    def index():
        page_number = connexion.request.headers['Page-Number']


Custom Validators
-----------------

By default, body and parameters contents are validated against OpenAPI schema
via ``connexion.decorators.validation.RequestBodyValidator``
or ``connexion.decorators.validation.ParameterValidator``, if you want to
change the validation, you can override the defaults with:

.. code-block:: python

    validator_map = {
        'body': CustomRequestBodyValidator,
        'parameter': CustomParameterValidator
    }
    app = connexion.FlaskApp(__name__)
    app.add_api('api.yaml', ..., validator_map=validator_map)

See custom validator example in ``examples/enforcedefaults``.
