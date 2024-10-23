Security
========

Connexion implements a pluggable security validation mechanism and provides built-in support for
some of the most popular security schemes.

.. csv-table::
    :widths: 30, 70
    :header-rows: 1

    **Swagger 2**, **Connexion support**
    Basic Authentication, |:white_check_mark:|
    API key, |:white_check_mark:|
    Oauth2, |:white_check_mark:|
    **OpenAPI**,
    HTTP Basic, |:white_check_mark:|
    HTTP Bearer, |:white_check_mark:|
    Other HTTP schemes (RFC 7253), "No built-in support, use a `custom security handler <#custom-security-handlers>`_"
    API key, |:white_check_mark:|
    Oauth2, |:white_check_mark:|
    OpenID, "No built-in support, use a `custom security handler <#custom-security-handlers>`_"

General authentication flow
---------------------------

For each supported authentication type, Connexion lets you register a validation function to
validate the incoming credentials, and return information about the authenticated user.

The validation function must either be defined in the API security definition
as ``x-{type}InfoFunc``, or in the environment variables as ``{TYPE}INFO_FUNC``. The function
should be referenced as a string using the same syntax that is used to connect an ``operationId``
to a Python function when :ref:`routing <Routing:Explicit routing>`. Note that even if you used a resolver for the operation id, it is not applied to the validation function, and you need to specify the complete path to the security module

While the validation functions should accept different arguments based on the authentication type
(as documented below), they should all return a dict which complies with `RFC 7662 <rfc7662_>`_:

.. code-block:: json

    {
      "active": true,
      "client_id": "l238j323ds-23ij4",
      "username": "jdoe",
      "scope": "read write dolphin",
      "sub": "Z5O3upPC88QrAjx00dis",
      "aud": "https://protected.example.net/resource",
      "iss": "https://server.example.com/",
      "exp": 1419356238,
      "iat": 1419350238,
      "extension_field": "twenty-seven"
    }

The token information is made available to your endpoint view functions via the
:ref:`context <context:context.context>`, which you can also have passed in as an
:ref:`argument <request:Context>`.

.. note::

    Note that you are responsible to validate any fields other than the scopes yourself.

.. _rfc7662: https://tools.ietf.org/html/rfc7662

Basic Authentication
--------------------

For Basic authentication, the API security definition must include an
``x-basicInfoFunc`` definition or set the ``BASICINFO_FUNC`` environment variable.

The function should accept the following arguments:

- username
- password
- required_scopes (optional)
- request (optional)

You can find a `minimal Basic Auth example application`_ in Connexion's "examples" folder.

.. _minimal Basic Auth example application: https://github.com/spec-first/connexion/tree/main/examples/basicauth

Bearer Authentication (JWT)
---------------------------

For Bearer authentication (JWT), the API security definition must include an
``x-bearerInfoFunc`` definition or set the ``BEARERINFO_FUNC`` environment variable.

The function should accept the following arguments:

- token
- required_scopes (optional)
- request (optional)

You can find a `minimal Bearer example application`_ in Connexion's "examples" folder.

.. _minimal Bearer example application: https://github.com/spec-first/connexion/tree/main/examples/jwt

ApiKey Authentication
---------------------

For API key authentication, the API security definition must include an
``x-apikeyInfoFunc`` definition or set the ``APIKEYINFO_FUNC`` environment variable.

The function should accept the following arguments:

- apikey
- required_scopes (optional)
- request (optional)

You can find a `minimal API Key example application`_ in Connexion's "examples" folder.

.. _minimal API Key example application: https://github.com/spec-first/connexion/tree/main/examples/apikey

OAuth 2 Authentication and Authorization
----------------------------------------

For OAuth authentication, the API security definition must include an
``x-tokenInfoFunc`` definition or set the ``TOKENINFO_FUNC`` environment variable.

The function should accept the following arguments:

- token
- required_scopes (optional)
- request (optional)

As alternative to an ``x-tokenInfoFunc`` definition, you can set an ``x-tokenInfoUrl`` definition or
``TOKENINFO_URL`` environment variable, and connexion will call the url instead of a local
function instead. Connexion expects the authorization server to receive the OAuth token in the
``Authorization`` header field in the format described in `RFC 6750 <rfc6750_>`_ section 2.1 and
return the token information in the same format as a validation function. When both
``x-tokenInfoUrl`` and ``x-tokenInfoFunc`` are used, Connexion will prioritize the function.

The list of scopes returned in the token information will be validated against the scopes
required by the API security definition to determine if the user is authorized.
You can supply a custom scope validation func by defining ``x-scopeValidateFunc``
or setting a ``SCOPEVALIDATE_FUNC`` environment variable.

The function should accept the following arguments:

- required_scopes
- token_scopes
- request (optional)

and return a boolean indicating if the validation was successful.

Deprecated features, retained for backward compatibility:

- ``scope`` field can also be named ``scopes``.
- ``sub`` field can also be named ``uid``.

You can find a `minimal OAuth example application`_ showing the use of
``x-tokenInfoUrl``, and `another OAuth example`_ showing the use of
``x-tokenInfoFunc`` in Connexion's "examples" folder.

.. _minimal OAuth example application: https://github.com/spec-first/connexion/tree/main/examples/oauth2
.. _another OAuth example: https://github.com/spec-first/connexion/tree/main/examples/oauth2_local_tokeninfo
.. _rfc6750: https://tools.ietf.org/html/rfc6750

Multiple Authentication Schemes
-------------------------------

With Connexion, it is also possible to combine multiple authentication schemes
as described in the `OpenAPI specification`_. When multiple authentication
schemes are combined using logical AND, the ``token_info`` argument will
consist of a dictionary mapping the names of the security scheme to their
corresponding ``token_info``.

Multiple OAuth2 security schemes in AND fashion are not supported.

.. _OpenAPI specification: https://swagger.io/docs/specification/authentication/#multiple

Custom security handlers
------------------------

You can implement your own security handlers for schemes that are not supported yet in Connexion
by subclassing the ``connexion.security.AbstractSecurityHandler`` class and passing it in a custom
``security_map`` to your application or API:

.. code-block:: python
    :caption: **app.py**

    from connexion.security import AbstractSecurityHandler


    class MyCustomSecurityHandler(AbstractSecurityHandler):

        security_definition_key = "x-{type}InfoFunc"
        environ_key = "{TYPE}INFO_FUNC"

        def _get_verify_func(self, {type}_info_func):
        ...

    security_map = {
        "{type}": MyCustomSecurityHandler,
    }

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import AsyncApp

            app = AsyncApp(__name__, security_map=security_map)
            app.add_api("openapi.yaml", security_map=security_map)


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import FlaskApp

            app = FlaskApp(__name__, security_map=security_map)
            app.add_api("openapi.yaml", security_map=security_map)

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app, security_map=security_map)
            app.add_api("openapi.yaml", security_map=security_map)

.. note::

    If you implement a custom security handler, and think it would be valuable for other users, we
    would appreciate it as a contribution.
