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
| Swagger Type | Python Type |
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

In the Swagger definition if the `array` type is used you can define the
`collectionFormat` that it should be recognized. Connexion currently
supports collection formats "pipes" and "csv". The default format is "csv".

.. note:: For more details about `collectionFormat`'s please check the
          official `Swagger/OpenAPI specification`_.

.. _jsonschema: https://pypi.python.org/pypi/jsonschema
.. _`Swagger/OpenAPI specification`: https://github.com/OAI/OpenAPI-Specification/blob/OpenAPI.next/versions/2.0.md#fixed-fields-7

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
