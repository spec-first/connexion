Middleware
==========

Connexion is built as an ASGI middleware stack wrapping an application. It includes several
middlewares by default that add functionality based on the OpenAPI specification, in the
following order:

.. csv-table::
    :widths: 30, 70

    **ServerErrorMiddleware**, "Returns server errors for any exceptions not caught by the
    ExceptionMiddleware"
    **ExceptionMiddleware**, Handles exceptions raised by the middleware stack or application
    **SwaggerUIMiddleware**, Adds a Swagger UI to your application
    **RoutingMiddleware**, "Routes incoming requests to the right operation defined in the
    specification"
    **SecurityMiddleware**, "Checks incoming requests against the security defined in the
    specification"
    **RequestValidationMiddleware**, Validates the incoming requests against the spec
    **ResponseValidationMiddleware**, "Validates the returned responses against the spec, if
    activated"
    **LifespanMiddleware**, "Allows registration of code to run before application start-up or
    after shut-down"
    **ContextMiddleware**, "Makes several request scoped context variables available to the
    application"

Adding middleware
-----------------

You can easily add additional ASGI middleware to the middleware stack with the
:code:`add_middleware` method:

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python

            from connexion import AsyncApp

            app = AsyncApp(__name__)

            app.add_middleware(MiddlewareClass, **options)

        .. dropdown:: View a detailed reference of the :code:`add_middleware` method
            :icon: eye

            .. automethod:: connexion.AsyncApp.add_middleware
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python

            from connexion import FlaskApp

            app = FlaskApp(__name__)

            app.add_middleware(MiddlewareClass, **options)

        .. dropdown:: View a detailed reference of the :code:`add_middleware` method
            :icon: eye

            .. automethod:: connexion.FlaskApp.add_middleware
                :noindex:

        You can also add WSGI middleware to a ``FlaskApp``. Note that it will only be called at the
        end of the middleware stack. If you need your middleware to act sooner, you will have to
        use an ASGI middleware instead.

        .. code-block:: python

            app.add_wsgi_middleware(MiddlewareClass, **options)

        .. dropdown:: View a detailed reference of the :code:`add_middleware` method
            :icon: eye

            .. automethod:: connexion.FlaskApp.add_wsgi_middleware
                :noindex:

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app)

            app.add_middleware(MiddlewareClass, **options)

        .. dropdown:: View a detailed reference of the :code:`add_wsgi_middleware` method
            :icon: eye

            .. automethod:: connexion.ConnexionMiddleware.add_middleware
                :noindex:

Middleware order
****************

The :code:`add_middleware` method takes a :code:`position` argument to define where in the
middleware stack it should be inserted, which should be an instance of the
:class:`~connexion.middleware.MiddlewarePosition` Enum. The positions below are ordered from
outer to inner, in the order they are hit by incoming requests. Note that responses hit the
middlewares in reversed order.

.. autoclass:: connexion.middleware.MiddlewarePosition
    :members:
    :member-order: bysource

Customizing the middleware stack
--------------------------------

If you need more flexibility, or want to modify or delete any of the default middlewares, you can
also pass in a customized middleware stack when instantiating your application.

For example, if you would like to remove the :class:`SecurityMiddleware` since you are handling
Security through an API Gateway in front of your application, you can do:

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python

            from connexion import AsyncApp, ConnexionMiddleware
            from connexion.middleware.security import SecurityMiddleware

            middlewares = [middleware for middleware in ConnexionMiddleware.default_middlewares
                           if middleware is not SecurityMiddleware]

            app = AsyncApp(__name__, middlewares=middlewares)

        .. dropdown:: View a detailed reference of the :class:`~connexion.AsyncApp`
            :code:`__init__` method
            :icon: eye

            .. autoclass:: connexion.AsyncApp
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python

            from connexion import FlaskApp, ConnexionMiddleware
            from connexion.middleware.security import SecurityMiddleware

            middlewares = [middleware for middleware in ConnexionMiddleware.default_middlewares
                           if middleware is not SecurityMiddleware]

            app = FlaskApp(__name__, middlewares=middlewares)

        .. dropdown:: View a detailed reference of the :class:`~connexion.FlaskApp`
            :code:`__init__` method
            :icon: eye

            .. autoclass:: connexion.FlaskApp
                :noindex:


    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python

            from asgi_framework import App
            from connexion import ConnexionMiddleware
            from connexion.middleware.security import SecurityMiddleware

            middlewares = [middleware for middleware in ConnexionMiddleware.default_middlewares
                           if middleware is not SecurityMiddleware]

            app = App(__name__)
            app = ConnexionMiddleware(app, middlewares=middlewares)

        .. dropdown:: View a detailed reference of the :class:`~connexion.ConnexionMiddleware`
            :code:`__init__` method
            :icon: eye

            .. autoclass:: connexion.ConnexionMiddleware
                :noindex:


Writing custom middleware
-------------------------

You can add any custom middleware as long as it implements the ASGI interface. To learn how to
write pure ASGI middleware, please refer to the `documentation of starlette`_.

List of useful middleware
-------------------------

Starlette provides a bunch of useful middleware such as:

* `CORSMiddleware`_
* `SessionMiddleware`_
* `HTTPSRedirectMiddleware`_
* `TrustedHostMiddleware`_
* `GZipMiddleware`_

Other useful middleware:

* `ProxyHeadersMiddleware`_ by Uvicorn
* `SentryASGIMiddleware`_ by Sentry
* `MetricsMiddleware`_ by Prometheus

For more, check the `asgi-middleware topic`_ on github.

.. _documentation of starlette: https://www.starlette.io/middleware/#writing-pure-asgi-middleware
.. _CORSMiddleware: https://www.starlette.io/middleware/#corsmiddleware
.. _SessionMiddleware: https://www.starlette.io/middleware/#sessionmiddleware
.. _HTTPSRedirectMiddleware: https://www.starlette.io/middleware/#httpsredirectmiddleware
.. _TrustedHostMiddleware: https://www.starlette.io/middleware/#trustedhostmiddleware
.. _GZipMiddleware: https://www.starlette.io/middleware/#gzipmiddleware
.. _ProxyHeadersMiddleware: https://github.com/encode/uvicorn/blob/master/uvicorn/middleware/proxy_headers.py
.. _SentryASGIMiddleware: https://docs.sentry.io/platforms/python/configuration/integrations/asgi/
.. _MetricsMiddleware: https://github.com/claws/aioprometheus/blob/master/src/aioprometheus/asgi/middleware.py
.. _asgi-middleware topic: https://github.com/topics/asgi-middleware
