Apps & APIs
===========

Connexion can be used either as a standalone application or as a middleware wrapping an existing
ASGI (or WSGI) application written using a different framework. The standalone application can be
built using either the :code:`AsyncApp` or :code:`FlaskApp`.

- The :code:`AsyncApp` is a lightweight application with native asynchronous support. Use it if you
  are starting a new project and have no specific reason to use one of the other options.
- The :code:`FlaskApp` leverages the `Flask` framework, which is useful if you're migrating from
  connexion 2.X or you want to leverage the `Flask` ecosystem.
- The :code:`ConnexionMiddleware` can be wrapped around any existing ASGI or WSGI application.
  Use it if you already have an application written in a different framework and want to add
  functionality provided by connexion.

Creating your application
-------------------------

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python

            from connexion import AsyncApp

            app = AsyncApp(__name__)

        .. dropdown:: View a detailed reference of the options accepted by the :code:`AsyncApp`
            :icon: eye

            .. autoclass:: connexion.AsyncApp
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. note::
            To leverage the :code:`FlaskApp`, make sure you install connexion using the
            :code:`flask` extra.

        .. code-block:: python

            from connexion import FlaskApp

            app = FlaskApp(__name__)

        .. dropdown:: View a detailed reference of the options accepted by the :code:`FlaskApp`
            :icon: eye

            .. autoclass:: connexion.FlaskApp
                :noindex:

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python

            from asgi_framework import App
            from connexion import ConnexionMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app)


        You can also wrap a WSGI application leveraging the :code:`a2wsgi.WSGIMiddleware`:

        .. code-block:: python

            from wsgi_framework import App
            from connexion import ConnexionMiddleware
            from a2wsgi import WSGIMiddleware

            wsgi_app = App(__name__)
            asgi_app = WSGIMiddleware(wsgi_app)
            app = ConnexionMiddleware(app)

        .. dropdown:: View a detailed reference of the options accepted by the
            :code:`ConnexionMiddleware`
            :icon: eye

            .. autoclass:: connexion.ConnexionMiddleware
                :noindex:

Registering an API
------------------

While you can register individual routes on your application, connexion really shines when you
register an API defined by an OpenAPI (or Swagger) specification. You can add as many APIs as you
want to a single application.

When an argument is provided both on the App and the API, the API value will take precedence.

.. code-block:: python

    app.add_api("openapi.yaml")

.. dropdown:: View a detailed reference of the options accepted by the :code:`add_api()` method
    :icon: eye

    .. tab-set::

        .. tab-item:: AsyncApp
            :sync: AsyncApp

            .. autofunction:: connexion.AsyncApp.add_api
                :noindex:

        .. tab-item:: FlaskApp
            :sync: FlaskApp

            .. autofunction:: connexion.FlaskApp.add_api
                :noindex:

        .. tab-item:: ConnexionMiddleware
            :sync: ConnexionMiddleware

            .. autofunction:: connexion.ConnexionMiddleware.add_api
                :noindex:

Running your application
------------------------

You can run your application using an ASGI server such as `uvicorn`. If you defined your
:code:`app` in a python module called :code:`run.py`, you can run it as follows:

.. code-block:: bash

    $ uvicorn run:app

or if you installed connexion using :code:`connexion[uvicorn]`, you can run it using the
:code:`run` method, although this is only recommended for development:

.. code-block:: python

    app.run()

To leverage automatic reloading of your application, you need to provide the application as an
import string. In most cases, this can be achieved as follows:

.. code-block:: python

    from pathlib import Path

    app.run(f"{Path(__file__).stem}:app")

.. dropdown:: View a detailed reference of the options accepted by the :code:`run()` method
    :icon: eye

    .. tab-set::

        .. tab-item:: AsyncApp
            :sync: AsyncApp

            .. autofunction:: connexion.AsyncApp.run
                :noindex:

        .. tab-item:: FlaskApp
            :sync: FlaskApp

            .. autofunction:: connexion.FlaskApp.run
                :noindex:

        .. tab-item:: ConnexionMiddleware
            :sync: ConnexionMiddleware

            .. autofunction:: connexion.ConnexionMiddleware.run
                :noindex:

Full class reference
--------------------

.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. dropdown:: View a detailed reference of the :code:`AsyncApp`
            :icon: eye

            .. autoclass:: connexion.AsyncApp
                :members:
                :undoc-members:
                :inherited-members:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. dropdown:: View a detailed reference of the :code:`FlaskApp`
            :icon: eye

            .. autoclass:: connexion.FlaskApp
                :members:
                :undoc-members:
                :inherited-members:

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. dropdown:: View a detailed reference of the :code:`ConnexionMiddleware`
            :icon: eye

            .. autoclass:: connexion.ConnexionMiddleware
                :members:
                :undoc-members:
