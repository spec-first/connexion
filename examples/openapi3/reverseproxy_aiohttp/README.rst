=====================
Reverse Proxy Example
=====================

This example demonstrates how to run a connexion application behind a path-altering reverse proxy.

You can either set the path in your app, or set the ``X-Forwarded-Path`` header.

Running:

.. code-block:: bash

    $ sudo pip3 install --upgrade connexion[swagger-ui] aiohttp-remotes  
    $ ./app.py

Now open your browser and go to http://localhost:8080/reverse_proxied/ui/ to see the Swagger UI.


You can also use the ``X-Forwarded-Path`` header to modify the reverse proxy path.
For example:

.. code-block:: bash

    curl -H "X-Forwarded-Path: /banana/" http://localhost:8080/openapi.json

    {
       "servers" : [
          {
             "url" : "banana"
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

