Lifespan
========

You can register lifespan handlers to run code before the app starts, or after it shuts down.
This ideal for setting up and tearing down database connections or machine learning models for
instance.

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python

            import contextlib
            import typing

            from connexion import AsyncApp, ConnexionMiddleware, request

            @contextlib.asynccontextmanager
            async def lifespan_handler(app: ConnexionMiddleware) -> typing.AsyncIterator:
                """Called at startup and shutdown, can yield state which will be available on the
                 request."""
                client = Client()
                yield {"client": client}
                client.close()

            def route():
                """Endpoint function called when receiving a request, you can access the state
                on the request here."""
                client = request.state.client
                client.call()

            app = AsyncApp(__name__, lifespan=lifespan_handler)

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python

            import contextlib
            import typing

            from connexion import FlaskApp, ConnexionMiddleware, request

            @contextlib.asynccontextmanager
            async def lifespan_handler(app: ConnexionMiddleware) -> typing.AsyncIterator:
                """Called at startup and shutdown, can yield state which will be available on the
                 request."""
                client = Client()
                yield {"client": client}
                client.close()

            def route():
                """Endpoint function called when receiving a request, you can access the state
                on the request here."""
                client = request.state.client
                client.call()

            app = FlaskApp(__name__, lifespan=lifespan_handler)

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python

            import contextlib
            import typing

            from asgi_framework import App
            from connexion import ConnexionMiddleware, request

            @contextlib.asynccontextmanager
            async def lifespan_handler(app: ConnexionMiddleware) -> typing.AsyncIterator:
                """Called at startup and shutdown, can yield state which will be available on the
                 request."""
                client = Client()
                yield {"client": client}
                client.close()

            def endpoint():
                """Endpoint function called when receiving a request, you can access the state
                on the request here."""
                client = request.state.client
                client.call()

            app = App(__name__)
            app = ConnexionMiddleware(app, lifespan=lifespan_handler)

Running lifespan in tests
-------------------------

If you want lifespan handlers to be called during tests, you can use the ``test_client`` as a
context manager.

.. code-block:: python

    def test_homepage():
        app = ...  # Set up app
        with app.test_client() as client:
            # Application's lifespan is called on entering the block.
            response = client.get("/")
            assert response.status_code == 200

        # And the lifespan's teardown is run when exiting the block.

For more information, please refer to the `Starlette documentation`_.

.. _Starlette documentation: https://www.starlette.io/lifespan/
