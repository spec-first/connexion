Response Handling
=================

When your application returns a response, Connexion provides the following functionality based on
your OpenAPI spec:

- It automatically translates Python errors into HTTP problem responses (see :doc:`exceptions`)
- It automatically serializes the response for certain content types
- It validates the response body and headers (see :doc:`validation`)

On this page, we zoom in on the response serialization.

Response Serialization
----------------------

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp


        When working with Connexion, you can return ordinary Python types, and connexion will serialize
        them into a network response.

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        When working with Connexion, you can return ordinary Python types, and connexion will serialize
        them into a network response.

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        When working with Connexion, you can return ordinary Python types, and connexion will serialize
        them into a network response.

        To activate this behavior when using the ``ConnexionMiddleware`` wrapping a third party
        application, you can leverage the following decorators provided by Connexion:

        * ``FlaskDecorator``: provides automatic parameter injection and response serialization for
          Flask applications.

          .. code-block:: python
              :caption: **app.py**

              from connexion import ConnexionMiddleware
              from connexion.decorators import FlaskDecorator
              from flask import Flask

              app = Flask(__name__)
              app = ConnexionMiddleware(app)
              app.add_api("openapi.yaml")

              @app.route("/endpoint")
              @FlaskDecorator()
              def endpoint(name):
                  ...

        * ``StarletteDecorator``: provides automatic parameter injection and response serialization
          for Starlette applications.

          .. code-block:: python
              :caption: **app.py**

              from connexion import ConnexionMiddleware
              from connexion.decorators import StarletteDecorator
              from starlette.applications import Starlette
              from starlette.routing import Route

              @StarletteDecorator()
              def endpoint(name):
                  ...

              app = Starlette(routes=[Route('/endpoint', endpoint)])
              app = ConnexionMiddleware(app)
              app.add_api("openapi.yaml")

        For a full example, see our `Frameworks`_ example.

        The generic ``connexion.decorators.WSGIDecorator`` and
        ``connexion.decorators.ASGIDecorator`` unfortunately don't support response
        serialization, but you can extend them to implement your own decorator for a specific
        WSGI or ASGI framework respectively.

        .. note::

            If you implement a custom decorator, and think it would be valuable for other users, we
            would appreciate it as a contribution.

.. code-block:: python
    :caption: **api.py**

    def endpoint():
        data = "success"
        status_code = 200
        headers = {"Content-Type": "text/plain"}
        return data, status_code, headers

Data
````

If your API returns responses with the ``application/json`` content type, you can return
a simple ``dict`` or ``list`` and Connexion will serialize (``json.dumps``) the data for you.

**Customizing JSON serialization**

Connexion allows you to customize the ``Jsonifier`` used to serialize json data by subclassing the
``connexion.jsonifier.Jsonifier`` class and passing it when instantiating your app or registering
an API:

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import AsyncApp

            app = AsyncApp(__name__, jsonifier=)
            app.add_api("openapi.yaml", jsonifier=c)


    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
            :caption: **app.py**

            from connexion import FlaskApp

            app = FlaskApp(__name__, jsonifier=...)
            app.add_api("openapi.yaml", jsonifier=...):

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
            :caption: **app.py**

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app, jsonifier=...)
            app.add_api("openapi.yaml", jsonifier=...)

Status code
```````````

If no status code is provided, Connexion will automatically set it as ``200`` if data is
returned, or as ``204`` if ``None`` or ``connexion.datastructures.NoContent`` is returned.

Headers
```````

The headers can be used to define any response headers to return. If your OpenAPI specification
defines multiple responses with different content types, you can explicitly set the
``Content-Type`` header to tell Connexion which response to validate against.

If you do not explicitly return a ``Content-Type`` header, Connexion's behavior depends on the
Responses defined in your OpenAPI spec:

* If you have defined a single response content type in your OpenAPI specification, Connexion
  will automatically set it.
* If you have defined multiple response content types in your OpenAPI specification, Connexion
  will try to infer which one matches your response and set it. If it cannot infer the content
  type, an error is raised.
* If you have not defined a response content type in your OpenAPI specification, Connexion will
  automatically set it to ``application/json`` unless you don't return any data. This is mostly
  because of backward-compatibility, and can be circumvented easily by defining a response
  content type in your OpenAPI specification.

Skipping response serialization
-------------------------------

If your endpoint returns an instance of ``connexion.lifecycle.ConnexionResponse``, or a
framework-specific response (``flask.Response`` or ``starlette.responses.Response``), response
serialization is skipped, and the response is passed directly to the underlying framework.

If your endpoint returns a `Response`
If the endpoint returns a `Response` object this response will be used as is.

.. _Frameworks: https://github.com/spec-first/connexion/tree/main/examples/frameworks
