Exception Handling
==================

Connexion allows you to register custom error handlers to convert Python ``Exceptions`` into HTTP
problem responses.

You can register error handlers on:

- The exception class to handle
  If this exception class is raised somewhere in your application or the middleware stack,
  it will be passed to your handler.
- The HTTP status code to handle
  Connexion will raise ``starlette.HTTPException`` errors when it encounters any issues
  with a request or response. You can intercept these exceptions with specific status codes
  if you want to return custom responses.

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python

            from connexion import AsyncApp
            from connexion.lifecycle import ConnexionRequest, ConnexionResponse

            def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
                return ConnexionResponse(status_code=404, body=json.dumps({"error": "NotFound"}))

            app = AsyncApp(__name__)
            app.add_error_handler(FileNotFoundError, not_found)
            app.add_error_handler(404, not_found)

        .. dropdown:: View a detailed reference of the ``add_error_handler`` method
            :icon: eye

            .. automethod:: connexion.AsyncApp.add_error_handler
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python

            from connexion import FlaskApp
            from connexion.lifecycle import ConnexionRequest, ConnexionResponse

            def not_found(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
                return ConnexionResponse(status_code=404, body=json.dumps({"error": "NotFound"}))

            app = FlaskApp(__name__)
            app.add_error_handler(FileNotFoundError, not_found)
            app.add_error_handler(404, not_found)

        .. dropdown:: View a detailed reference of the ``add_error_handler`` method
            :icon: eye

            .. automethod:: connexion.FlaskApp.add_error_handler
                :noindex:

        .. note::

            .. warning::

                ⚠️ **The following is not recommended as it complicates the exception handling logic,**

            You can also register error handlers on the underlying flask application directly.

            .. code-block:: python

                flask_app = app.app
                flask_app.register_error_handler(FileNotFoundError, not_found)
                flask_app.register_error_handler(404, not_found)

            `Flask documentation`_

            Error handlers registered this way:

            - Will only intercept exceptions thrown in the application, not in the Connexion
              middleware.
            - Can intercept exceptions before they reach the error handlers registered on the
              connexion app.
            - When registered on status code, will intercept only
              ``werkzeug.exceptions.HTTPException`` thrown by werkzeug / Flask not
              ``starlette.exceptions.HTTPException``.

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

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

        .. dropdown:: View a detailed reference of the ``add_error_handler`` method
            :icon: eye

            .. automethod:: connexion.ConnexionMiddleware.add_error_handler
                :noindex:

        .. note::

            This might not catch ``HTTPExceptions`` with the same status code raised by
            your wrapped ASGI/WSGI framework.

.. note::

    Error handlers can be ``async`` coroutines as well.

.. _Flask documentation: https://flask.palletsprojects.com/en/latest/errorhandling/#error-handlers

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
