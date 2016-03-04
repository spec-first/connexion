Response Handling
=================

Response Serialization
----------------------
If the endpoint returns a `Response` object this response will be used as is.

Otherwise, and by default and if the specification defines that an endpoint
produces only JSON, connexion will automatically serialize the return value
for you and set the right content type in the HTTP header.

If the endpoint produces a single non JSON mimetype then Connexion will
automatically set the right content type in the HTTP header.

Returning status codes
----------------------
There are two ways of returning a specific status code.

One way is to return a `Response` object that will be used unchanged.

The other is returning it as second return value in the response. For example

.. code-block:: python

    def my_endpoint():
        return 'Not Found', 404

Returning Headers
-----------------
There are two ways to return headers from your endpoints.

One way is to return a `Response` object that will be used unchanged.

The other is returning a dict with the header values as the third return value
in the response:

For example

.. code-block:: python

    def my_endpoint():
        return 'Not Found', 404, {'x-error': 'not found'}


Response Validation
-------------------
While, by default Connexion doesn't validate the responses it's possible to
do so by opting in when adding the API:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', validate_responses=True)
    app.run(port=8080)

This will validate all the responses using `jsonschema` and is specially useful
during development.

Error Handling
--------------
By default connexion error messages are JSON serialized according to
`Problem Details for HTTP APIs <http_problem_>`_.

Application can return errors using ``connexion.problem``.

.. _http_problem: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
