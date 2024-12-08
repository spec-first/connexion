=====================
Reverse Proxy Example
=====================

This example demonstrates how to run a connexion application behind a path-altering reverse proxy.

You can set the path in three ways:

- Via the Middleware
.. code-block::

    app = ReverseProxied(app, root_path="/reverse_proxied/")

- Via the ASGI server
.. code-block::

    uvicorn ... --root_path="/reverse_proxied/"

- By using the ``X-Forwarded-Path`` header in your proxy server. Eg in nginx:
.. code-block::

    location /proxied {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Path /proxied;
    }

To run this example, install Connexion from PyPI:
.. code-block::

    $ pip install 'connexion[flask,swagger-ui,uvicorn]>=3.1.0'

and then run it either directly
.. code-block::

    $ python app.py

or using uvicorn (or another async server):
.. code-block::
    $ uvicorn --factory app:create_app --port 8080

If your proxy server is running at http://localhost:8080/revers_proxied/, you can go to
http://localhost:8080/reverse_proxied/openapi/ui/ to see the Swagger UI.

Or you can test this using the ``X-Forwarded-Path`` header to modify the reverse proxy path.
For example, note the servers block:

.. code-block:: bash

    curl -H "X-Forwarded-Path: /banana/" http://localhost:8080/openapi/openapi.json

    {
       "servers" : [
          {
             "url" : "/banana/openapi"
          }
       ],
       "paths" : {
          "/hello" : {
             "get" : {
                "responses" : {
                   "200" : {
                      "description" : "hello",
                      "content" : {
                         "text/plain" : {
                            "schema" : {
                               "type" : "string"
                            }
                         }
                      }
                   }
                },
                "operationId" : "app.hello",
                "summary" : "say hi"
             }
          }
       },
       "openapi" : "3.0.0",
       "info" : {
          "version" : "1.0",
          "title" : "Path-Altering Reverse Proxy Example"
       }
    }
