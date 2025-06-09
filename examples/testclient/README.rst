===================
Test Client Example
===================

This example demonstrates test and validation features for a
simple Connexion app:

* Validate generated JSON responses against the specification
* Catch and report exceptions raised while processing a request
* Use tox and the Starlette test client to test the app automatically.

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands::

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[flask,swagger-ui,uvicorn]>=3.1.0' tox

Testing
-------

Run automated tests on the app with this command::

    $ tox

Running
-------

Launch the Connexion server directly::

    $ python app.py

or using uvicorn (or another async server)::

    $ uvicorn --factory app:create_app --port 8080

Now open your browser and view the Swagger UI for these specification files:

* http://localhost:8080/openapi/ui/ for the OpenAPI 3 spec
* http://localhost:8080/swagger/ui/ for the Swagger 2 spec

Demonstrating
-------------

In the Swagger UI, click the "Try it out" button.  Send a request with a name
and the default message body. The app responds with a 200 status code and a
greeting message "Hello <name>". Next, demonstrate the app's validation features
by sending a request with one of the following values in the request body's
``message`` parameter:

* Message ``crash``: the app raises an exception, which is caught and reported by
  the custom exception handler. The response is an RFC 7807 "problem" response
  with ``type``, ``title``, ``detail`` and ``status`` fields.
* Message ``invalid``: the app generates an invalid response, which is detected
  and reported by Connexion. The response is an RFC 7807 "problem" response with
  the failed-validation message.
