Connexion Cookbook
==================

This page provides recipes with Connexion as an ingredient.

CORS
----

You can enable CORS (Cross-origin resource sharing) by leveraging the `CORSMiddleware`_ offered by
Starlette. You can add it to your application, ideally in front of the ``RoutingMiddleware``.


.. tab-set::

    .. tab-item:: AsyncApp
        :sync: AsyncApp

        .. code-block:: python
        
            from pathlib import Path

            from connexion import AsyncApp
            from connexion.middleware import MiddlewarePosition
            from starlette.middleware.cors import CORSMiddleware


            app = AsyncApp(__name__)

            app.add_middleware(
                CORSMiddleware,
                position=MiddlewarePosition.BEFORE_ROUTING,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            app.add_api("openapi.yaml")

            if __name__ == "__main__":
                app.run(f"{Path(__file__).stem}:app", port=8080)

        .. dropdown:: View a detailed reference of the ``add_middleware`` method
            :icon: eye

            .. automethod:: connexion.AsyncApp.add_middleware
                :noindex:

    .. tab-item:: FlaskApp
        :sync: FlaskApp

        .. code-block:: python
        
            from pathlib import Path

            from connexion import FlaskApp
            from connexion.middleware import MiddlewarePosition
            from starlette.middleware.cors import CORSMiddleware


            app = FlaskApp(__name__)

            app.add_middleware(
                CORSMiddleware,
                position=MiddlewarePosition.BEFORE_ROUTING,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            app.add_api("openapi.yaml")

            if __name__ == "__main__":
                app.run(f"{Path(__file__).stem}:app", port=8080)

        .. dropdown:: View a detailed reference of the ``add_middleware`` method
            :icon: eye

            .. automethod:: connexion.FlaskApp.add_middleware
                :noindex:

    .. tab-item:: ConnexionMiddleware
        :sync: ConnexionMiddleware

        .. code-block:: python
        
            from pathlib import Path

            from asgi_framework import App
            from connexion import ConnexionMiddleware
            from starlette.middleware.cors import CORSMiddleware

            app = App(__name__)
            app = ConnexionMiddleware(app)

            app.add_middleware(
                CORSMiddleware,
                position=MiddlewarePosition.BEFORE_ROUTING,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            app.add_api("openapi.yaml")

            if __name__ == "__main__":
                app.run(f"{Path(__file__).stem}:app", port=8080)


        .. dropdown:: View a detailed reference of the ``add_middleware`` method
            :icon: eye

            .. automethod:: connexion.ConnexionMiddleware.add_middleware
                :noindex:

.. _CORSMiddleware: https://www.starlette.io/middleware/#corsmiddleware
