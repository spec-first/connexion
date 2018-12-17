=====================
External Reverse Proxy Example
=====================

This example demonstrates how to run a connexion application behind an external reverse proxy with rewrite rule.

Setup NGINX reverse proxy:

.. code-block:: NGINX

    server {
      listen 9000;
      listen [::]:9000;

      server_name example.com;

      location /reverse_proxied/ {
        # Define the location of the proxy server to send the request to
        proxy_pass http://localhost:8080/;
        # Add prefix header
        proxy_set_header X-Forwarded-Prefix $scheme://$host:$server_port/reverse_proxied;
      }
    }


And start application:

.. code-block:: bash

    $ sudo pip3 install --upgrade connexion[swagger-ui]  # install Connexion from PyPI
    $ ./app.py

Swagger UI can be accessed with direct connexion:

    http://localhost:8080/v1/ui

And through NGINX proxy with rewrite rule:

    http://localhost:9000/reverse_proxied/v1/ui
