Exception Handling
==================
Rendering Exceptions through the Flask Handler
----------------------------------------------
Flask by default contains an exception handler, which connexion's app can proxy
to with the ``add_error_handler`` method. You can hook either on status codes
or on a specific exception type.

Connexion is moving from returning flask responses on errors to throwing exceptions
that are a subclass of ``connexion.problem``. So far exceptions thrown in the OAuth
decorator have been converted.

Default Exception Handling
--------------------------
By default connexion exceptions are JSON serialized according to
`Problem Details for HTTP APIs`_

Application can return errors using ``connexion.problem`` or exceptions that inherit from both
``connexion.ProblemException`` and a ``werkzeug.exceptions.HttpException`` subclass (for example
``werkzeug.exceptions.Forbidden``). An example of this is the ``connexion.exceptions.OAuthProblem``
exception

.. code-block:: python

    class OAuthProblem(ProblemException, Unauthorized):
        def __init__(self, title=None, **kwargs):
            super(OAuthProblem, self).__init__(title=title, **kwargs)

.. _Problem Details for HTTP APIs: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00

Examples of Custom Rendering Exceptions
---------------------------------------
To custom render an exception when you boot your connexion application you can hook into a custom
exception and render it in some sort of custom format. For example


.. code-block:: python

    import connexion
    from connexion.exceptions import OAuthResponseProblem

    def render_unauthorized(exception):
        return Response(response=json.dumps({'error': 'There is an error in the oAuth token supplied'}), status=401, mimetype="application/json")

    app = connexion.FlaskApp(__name__, specification_dir='./../swagger/', debug=False, swagger_ui=False)
    app = app.add_error_handler(OAuthResponseProblem, render_unauthorized)

Custom Exceptions
-----------------
There are several exception types in connexion that contain extra information to help you render appropriate
messages to your user beyond the default description and status code:

OAuthProblem
^^^^^^^^^^^^
This exception is thrown when there is some sort of validation issue with the Authorisation Header

OAuthResponseProblem
^^^^^^^^^^^^^^^^^^^^
This exception is thrown when there is a validation issue from your OAuth 2 Server. It contains a
``token_response`` property which contains the full http response from the OAuth 2 Server

OAuthScopeProblem
^^^^^^^^^^^^^^^^^
This scope indicates the OAuth 2 Server did not generate a token with all the scopes required. This
contains 3 properties
- ``required_scopes`` - The scopes that were required for this endpoint
- ``token_scopes`` - The scopes that were granted for this endpoint


