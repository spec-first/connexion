Exception Handling
==================

Connexion allows you to register custom error handlers to convert Python ``Exceptions`` into HTTP
problem responses.

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        You can register error handlers on:

        - The exception class to handle
          If this exception class is raised somewhere in your application or the middleware stack,
          it will be passed to your handler.
        - The HTTP status code to handle
          Connexion will raise ``starlette.HTTPException`` errors when it encounters any issues
          with a request or response. You can intercept these exceptions with specific status codes
          if you want to return custom responses.

        .. code-block:: python

            from connexion import AsyncApp
            from connexion.lifecycle import ConnexionRequest, ConnexionResponse

            def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
                return ConnexionResponse(status_code=404, body=json.dumps({"error": "NotFound"}))

            app = AsyncApp(__name__)
            app.add_error_handler(FileNotFoundError, not_found)
            app.add_error_handler(404, not_found)

        .. dropdown:: View a detailed reference of the :code:`add_middleware` method
            :icon: eye

            .. automethod:: connexion.AsyncApp.add_error_handler
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        You can register error handlers on:

        - The exception class to handle
          If this exception class is raised somewhere in your application or the middleware stack,
          it will be passed to your handler.
        - The HTTP status code to handle
          Connexion will raise ``starlette.HTTPException`` errors when it encounters any issues
          with a request or response. The underlying Flask application will raise
          ``werkzeug.HTTPException`` errors. You can intercept both of these exceptions with
          specific status codes if you want to return custom responses.

        .. code-block:: python

            from connexion import FlaskApp
            from connexion.lifecycle import ConnexionRequest, ConnexionResponse

            def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
                return ConnexionResponse(status_code=404, body=json.dumps({"error": "NotFound"}))

            app = FlaskApp(__name__)
            app.add_error_handler(FileNotFoundError, not_found)
            app.add_error_handler(404, not_found)

        .. dropdown:: View a detailed reference of the :code:`add_middleware` method
            :icon: eye

            .. automethod:: connexion.FlaskApp.add_error_handler
                :noindex:

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        You can register error handlers on:

        - The exception class to handle
          If this exception class is raised somewhere in your application or the middleware stack,
          it will be passed to your handler.
        - The HTTP status code to handle
          Connexion will raise ``starlette.HTTPException`` errors when it encounters any issues
          with a request or response. You can intercept these exceptions with specific status codes
          if you want to return custom responses.
          Note that this might not catch ``HTTPExceptions`` with the same status code raised by
          your wrapped ASGI/WSGI framework.

        .. code-block:: python

            from asgi_framework import App
            from connexion import ConnexionMiddleware
            from connexion.lifecycle import ConnexionRequest, ConnexionResponse

            def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
                return ConnexionResponse(status_code=404, body=json.dumps({"error": "NotFound"}))

            app = App(__name__)
            app = ConnexionMiddleware(app)

            app.add_error_handler(FileNotFoundError, not_found)
            app.add_error_handler(404, not_found)

        .. dropdown:: View a detailed reference of the :code:`add_middleware` method
            :icon: eye

            .. automethod:: connexion.ConnexionMiddleware.add_error_handler
                :noindex:

.. note::

    Error handlers can be ``async`` coroutines as well.

Default Exception Handling
--------------------------
By default connexion exceptions are JSON serialized according to
`Problem Details for HTTP APIs`_

Application can return errors using ``connexion.problem.problem`` or raise exceptions that inherit
either from ``connexion.ProblemException`` or one of its subclasses to achieve the same behavior.

Using this, we can rewrite the handler above:

.. code-block:: python

    from connexion.lifecycle import ConnexionRequest, ConnexionResponse
    from connexion.problem import problem

    def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
        return problem(
            title="NotFound",
            detail="The requested resource was not found on the server",
            status=404,
        )

.. dropdown:: View a detailed reference of the :code:`problem` function
    :icon: eye

    .. autofunction:: connexion.problem.problem

.. _Problem Details for HTTP APIs: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00

Connexion Exceptions
--------------------
There are several exception types in connexion that contain extra information to help you render appropriate
messages to your user beyond the default description and status code:

.. automodule:: connexion.exceptions
    :members:
    :show-inheritance:
    :member-order: bysource
