===================
Test Client Example
===================

This directory offers an example of using the Starlette test client
to test a Connexion app. The app processes JSON requests and responses
as specified with OpenAPI v2 (aka Swagger) or OpenAPI v3 file format.
The responses are validated against the spec, and an error handler
catches exceptions raised while processing a request. The tests are
run by `tox` which also reports code coverage.

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[flask,swagger-ui,uvicorn]>=3.1.0' tox

Testing
-------

Run the test suite and generate the coverage report with this command:

.. code-block:: bash

    $ tox

Running
-------

Launch the connexion server with this command:

.. code-block:: bash

    $ python -m hello.app

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec
