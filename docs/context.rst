Context
=======

The ``ContextMiddleware`` included in Connexion provides some information about the current request
context as thread-safe request-level global variables.

You can access them by importing them from ``connexion.context``:

.. code-block:: python

    from connexion.context import context, operation, receive, request, scope
    from connexion import request  # alias for connexion.context.request

Note that when trying to access these context variables outside of the request handling flow, or
without running the ``ContextMiddleware``, the following ``RuntimeError`` will be thrown:

.. code-block:: text

    RuntimeError: Working outside of operation context. Make sure your app is wrapped in a
    ContextMiddleware and you're processing a request while accessing the context.

See below for an explanation of the different variables.

request
-------

A ``Request`` object representing the incoming request. This is an instance of the
``ConnexionRequest``.

.. dropdown:: View a detailed reference of the ``ConnexionRequest`` class
    :icon: eye

    .. autoclass:: connexion.lifecycle.ConnexionRequest
        :noindex:
        :members:
        :undoc-members:
        :inherited-members:

Some of the methods and attributes are coroutines that can only be accessed from an ``async``
context. When using the ``FlaskApp``, you might want to import the Flask request instead:

.. code-block:: python

    from flask import request

operation
---------

An ``Operation`` object representing the matched operation from your OpenAPI specification.

.. tab-set::

    .. tab-item:: OpenAPI 3
        :sync: OpenAPI 3

        When using OpenAPI 3, this is an instance of the ``OpenAPIOperation`` class.

        .. dropdown:: View a detailed reference of the ``OpenAPIOperation`` class
            :icon: eye

            .. autoclass:: connexion.operations.OpenAPIOperation
                :members:
                :undoc-members:
                :inherited-members:

    .. tab-item:: Swagger 2
        :sync: Swagger 2

        When using Swagger 2, this is an instance of the ``Swagger2Operation`` class.

        .. dropdown:: View a detailed reference of the ``Swagger2Operation`` class
            :icon: eye

            .. autoclass:: connexion.operations.Swagger2Operation
                :members:
                :undoc-members:
                :inherited-members:

scope
-----

The ASGI scope as received by the ``ContextMiddleware``, thus containing any changes propagated by
upstream middleware. The ASGI scope is presented as a ``dict``. Please refer to the `ASGI spec`_
for more information on its contents.

context.context
---------------

A dict containing the information from the security middleware:

.. code-block:: python

    {
        "user": ...  # User information from authentication
        "token_info": ...  # Token information from authentication
    }

Third party or custom middleware might add additional fields to this.

receive
-------

.. warning:: Advanced usage

The receive channel as received by the ``ContextMiddleware``. Note that the receive channel might
already be read by other parts of Connexion (eg. when accessing the body via the ``Request``, or
when it is injected into your Python function), and that reading it yourself might make it
unavailable for those parts of the application.

The receive channel can only be accessed from an ``async`` context and is therefore not relevant
when using the ``FlaskApp``.

.. _ASGI spec: https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope