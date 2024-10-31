Validation
==========

One of the most powerful Connexion features is automatic validation based on your OpenAPI
specification.

Connexion validates:

- :ref:`Requests<validation:Request validation>`

  - :ref:`Parameters<validation:Parameter validation>`
  - :ref:`Body<validation:RequestBody validation>`
  - :ref:`Headers<validation:Request headers validation>`

- :ref:`Response<validation:Response validation>`

  - :ref:`Body<validation:ResponseBody validation>`
  - :ref:`Headers<validation:Response headers validation>`

The validation behavior can easily be customized with :ref:`validation:Custom validators`

Request validation
------------------

Connexion will validate any incoming requests against your specification and automatically
returns the correct 4XX error on failure.

Parameter validation
````````````````````

By default, Connexion checks all the request for any parameters defined in your specification and
validates them against their definition. This includes their schema (``type``, ``format``,
``range``, ...) and whether or not they are required or whether they can be ``null``.

You can turn on ``strict_validation`` if you want Connexion to disallow any extra parameters
that are not defined in your specification. You can set it either on the application or API level:

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import AsyncApp

            app = AsyncApp(__name__, strict_validation=True)
            app.add_api("openapi.yaml", strict_validation=True)


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import FlaskApp

            app = FlaskApp(__name__, strict_validation=True)
            app.add_api("openapi.yaml", strict_validation=True)

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app, strict_validation=True)
            app.add_api("openapi.yaml", strict_validation=True)

If parameter validation fails, Connexion will return a ``400 Bad Request`` response with
information on the failure in the description.

For more information on how parameters are handled in general, see
:ref:`request:Request handling`.

RequestBody validation
``````````````````````

Connexion can automatically validate a ``requestBody`` for ``json`` and ``formData`` content
types, for which it relies on `jsonschema`_. You can plug in your own validator for other content
types (see :ref:`validation:Custom validators`).

.. note::
    If the ``Content-Type`` header is not set in the request, Connexion will check your
    specification for which content types it accepts. If it only accepts a single content type,
    Connexion assumes the request to have this content type and will validate it accordingly. If
    your specification specifies no or multiple content types it accepts, Connexion will assume
    the request to have content type ``application/octet-stream; charset=utf-8`` and will skip
    ``requestBody`` validation.

If ``requestBody`` validation fails, Connexion will return a ``400 Bad Request`` response with
information on the failure in the description.

For more information on how the ``requestBody`` is handled in general, see
:ref:`request:Body`.

Request headers validation
``````````````````````````

Headers and cookies are also validated against your specification. If their validation fails,
Connexion will return a ``400 Bad Request`` response with information on the failure in the
description.

The ``Content-Type`` header is validated separately. If it fails validation, Connexion returns a
``415 Unsupported Media Type`` error.

.. note::
    If the ``Content-Type`` header is not set in the request, Connexion will make an assumption
    on the content type (see :ref:`validation:RequestBody validation`) and validate it against your
    spec, which might fail.

Response validation
-------------------

Connexion **will not validate outgoing responses by default** , but you can activate this by passing
the ``validate_responses`` argument to either your application or API:

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import AsyncApp

            app = AsyncApp(__name__, validate_responses=True)
            app.add_api("openapi.yaml", validate_responses=True)


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import FlaskApp

            app = FlaskApp(__name__, validate_responses=True)
            app.add_api("openapi.yaml", validate_responses=True)

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app, validate_responses=True)
            app.add_api("openapi.yaml", validate_responses=True)

ResponseBody validation
```````````````````````

Connexion has built-in validators for the ``application/json`` and ``text/plain`` content types.
If the content type is not explicitly set, Connexion will infer it (see :ref:`response:Headers`),
and validate the body using the corresponding validator.

Response headers validation
```````````````````````````

Connexion will check for any required response headers that are missing and will validate the
``Content-Type`` header against the responses defined in your specification.

.. note::
    If the content type is not explicitly set, Connexion will infer it
    (see :ref:`response:Headers`), and validate the inferred content type, which can still fail.

Custom validators
-----------------

Connexion provides a ``validator_map`` argument which you can use to pass in custom validators.
The default validators are defined in ``connexion.validators.VALIDATOR_MAP``:

.. code-block:: python
    :caption: **connexion.validators**

    VALIDATOR_MAP = {
        "parameter": ParameterValidator,
        "body": MediaTypeDict(
            {
                "*/*json": JSONRequestBodyValidator,
                "application/x-www-form-urlencoded": FormDataValidator,
                "multipart/form-data": MultiPartFormDataValidator,
            }
        ),
        "response": MediaTypeDict(
            {
                "*/*json": JSONResponseBodyValidator,
                "text/plain": TextResponseBodyValidator,
            }
        ),
    }

Note that the ``"body"`` and ``"response"`` values are instances of the special ``MediaTypeDict``
datastructure, which can handle Media Type ranges:

.. autoclass:: connexion.datastructures.MediaTypeDict

You can create your own custom Validator by subclassing the
``connexion.validators.AbstractRequestBodyValidator`` or
``connexion.validators.AbstractResponseBodyValidator`` class and override the defaults by passing
in a custom ``validator_map`` to your application or API:

.. code-block:: python
    :caption: **app.py**

    from connexion.datastructures import MediaTypeDict
    from connexion.validators import AbstractResponseBodyValidator, TextResponseBodyValidator


    class MyCustomXMLResponseValidator(AbstractResponseBodyValidator):

        def _parse(self, stream: t.Generator[bytes, None, None]) -> t.Any:
            ...

        def _validate(self, body: dict):
            ...


    validator_map = {
        "response": MediaTypeDict(
            {
                "*/*json": JSONResponseBodyValidator,
                "*/*xml": MyCustomXMLResponseValidator,
                "text/plain": TextResponseBodyValidator,
            }
        ),
    }

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import AsyncApp

            app = AsyncApp(__name__, validator_map=validator_map)
            app.add_api("openapi.yaml", validator_map=validator_map)


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import FlaskApp

            app = FlaskApp(__name__, validator_map=validator_map)
            app.add_api("openapi.yaml", validator_map=validator_map)

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app, validator_map=validator_map)
            app.add_api("openapi.yaml", validator_map=validator_map)


Note that this will override the ``"response"`` section of the default ``VALIDATOR_MAP``, and
the ``"response"`` section only. This means that you need to include all ``ResponseValidators``
that you want to be active, or they will be removed.

If you want to deactivate request validation, you can pass in an empty dictionary:

.. code-block:: python

    validator_map = {
        "body": {}
    }

Which you then pass into your application or API as mentioned above.

Inserting requestBody defaults
``````````````````````````````

You can let Connexion automatically insert default values as defined in your specification into
an incoming ``requestBody`` by configuring the ``DefaultsJSONRequestBodyValidator``:

.. code-block:: python
    :caption: **app.py**

    from connexion.datastructures import MediaTypeDict
    from connexion.validators import (
        DefaultsJSONRequestBodyValidator,
        FormDataValidator,
        MultiPartFormDataValidator,
    )

    validator_map = {
        "body": MediaTypeDict(
            {
                "*/*json": DefaultsJSONRequestBodyValidator,
                "application/x-www-form-urlencoded": FormDataValidator,
                "multipart/form-data": MultiPartFormDataValidator,
            }
        ),
    }

Which you then pass into your application or API as mentioned above.

See our `enforce defaults`_ example for a full example.

Custom type formats
-------------------

It is possible to define custom type formats for validation without adding a custom validator, by
leveraging the ``jsonschema.Draft4Validator.FORMAT_CHECKER.checks`` decorator.

We can for instance create a custom `money` format.

.. code-block:: python

    import re
    from jsonschema import Draft4Validator

    MONEY_RE = re.compile('^\$\s*\d+(\.\d\d)?')

    @Draft4Validator.FORMAT_CHECKER.checks('money')
    def is_money(val):
        if not isinstance(val, str):
            return True
        return MONEY_RE.match(val)


Which you can then use in your openAPI specification:

.. code-block:: yaml

    type: object
    properties:
      title:
        type: string
      price_label:
        type: string
        format: money


The format checker function is expected to return ``True`` when the
value matches the expected format and return ``False`` when it
doesn't. Also is important to verify if the type of the value you are
trying to validate is compatible with the format. In our example we
check if the ``val`` is of type "string" before performing any further
checking.

.. note::

    Keep in mind that the format checkers should be defined and registered before you run your
    application server.

.. _enforce defaults: https://github.com/spec-first/connexion/tree/main/examples/enforcedefaults
.. _jsonschema: https://github.com/python-jsonschema/jsonschema