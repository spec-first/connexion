Quickstart
==========

Installation
------------

Make sure you are on Python 3.7+.

You can install connexion using pip:

.. code-block:: bash

    $ pip install connexion

Connexion provides extras with optional dependencies to unlock additional features:

- :code:`flask`: Enables the :code:`FlaskApp` to build applications compatible with the Flask
  ecosystem.
- :code:`swagger-ui`: Enables a Swagger UI console for your application.
- :code:`uvicorn`: Enables to run the your application using :code:`app.run()` for
  development instead of using an external ASGI server.

You can install them as follows:

.. code-block:: bash

    $ pip install connexion[<extra>]
    $ pip install connexion[<extra1>,<extra2>]


Creating your application
-------------------------

Create a minimal application based on an OpenAPI specification:

**run.py**

.. code-block:: python

    from connexion import AsyncApp

    app = AsyncApp(__name__)
    app.add_api("openapi.yaml")

Creating a Flask application
----------------------------

When installing connexion with the :code:`flask` extra, the :code:`FlaskApp` becomes available to
create an application using `Flask` underneath. This can be useful for compatibility with the
`Flask` ecosystem, but has limited asynchronous functionality.

**run.py**

.. code-block:: python

    from connexion import FlaskApp

    app = FlaskApp(__name__)
    app.add_api("openapi.yaml")

Running your application
------------------------

You can run your application using an ASGI server such as `uvicorn`:

.. code-block:: bash

    uvicorn run:app

or if you installed connexion using :code:`connexion[uvicorn]`, you can run it using the
:code:`run` method, although this is only recommended for development:

.. code-block:: python

    app.run()

The Swagger UI
--------------

If you installed connexion using the :code:`swagger-ui` extra, a Swagger UI is available for each
API. By default the UI is hosted at :code:`{base_path}/ui/` where :code:`base_path`` is the base
path of the API.

.. code-block::

    https://localhost:{port}/{base_path}/ui/

Using connexion as middleware to wrap an ASGI (or WSGI) application
-------------------------------------------------------------------

Connexion can also be used as middleware to add its functionality to existing ASGI application
written in a different framework (such as Starlette, Quart, Django, ...):

.. code-block:: python

    from asgi_framework import App
    from connexion import ConnexionMiddleware

    app = App(__name__)
    app = ConnexionMiddleware(app)
    app.add_api("openapi.yaml")

You can also wrap any WSGI application by wrapping it in a :code:`WSGIMiddleware`:

.. code-block:: python

    from wsgi_framework import App
    from connexion import ConnexionMiddleware
    from a2wsgi import WSGIMiddleware


    wsgi_app = App(__name__)
    asgi_app = WSGIMiddleware(wsgi_app)
    app = ConnexionMiddleware(app)
    app.add_api("openapi.yaml")


Configuring your API
--------------------

You can configure your application on the App level or on the API level. When an argument is
provided both on the App and the API, the API value will take precedence.

.. code-block:: python

    app = connexion.App(__name__, strict_validation=True)
    app.add_api("openapi.yaml", strict_validation=True)

