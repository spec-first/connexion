================
JWT Auth Example
================

.. note::

    jwt is not supported by swagger 2.0: https://swagger.io/docs/specification/2-0/authentication/

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[flask,swagger-ui,uvicorn]>=3.1.0'
    $ pip install -r requirements.txt

Running
-------

Launch the connexion server with this command:

.. code-block:: bash

    $ python app.py

Now open your browser and view the Swagger UI for the specification file:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec

Use endpoint **/auth** to generate JWT token, copy it, then click **Authorize** button and paste the token.
Now you can use endpoint **/secret** to check authentication.
