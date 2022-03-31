Response Handling
=================

Response Serialization
----------------------
If the endpoint returns a `Response` object this response will be used as is.

Otherwise, and by default and if the specification defines that an endpoint
produces only JSON, especifico will automatically serialize the return value
for you and set the right content type in the HTTP header.

If the endpoint produces a single non-JSON mimetype then Específico will
automatically set the right content type in the HTTP header.

Customizing JSON encoder
^^^^^^^^^^^^^^^^^^^^^^^^

Específico allows you to customize the `JSONEncoder` class in the Flask app
instance `json_encoder` (`especifico.App:app`). If you wanna reuse the
Específico's date-time serialization, inherit your custom encoder from
`especifico.apps.flask_app.FlaskJSONEncoder`.

For more information on the `JSONEncoder`, see the `Flask documentation`_.

.. _Flask Documentation: https://flask.palletsprojects.com/en/2.0.x/api/#flask.json.JSONEncoder

Returning status codes
----------------------
There are two ways of returning a specific status code.

One way is to return a `Response` object that will be used unchanged.

The other is returning it as a second return value in the response. For example

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
While, by default Específico doesn't validate the responses it's possible to
do so by opting in when adding the API:

.. code-block:: python

    import especifico

    app = especifico.FlaskApp(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', validate_responses=True)
    app.run(port=8080)

This will validate all the responses using `jsonschema` and is specially useful
during development.


Custom Validator
-----------------

By default, response body contents are validated against OpenAPI schema
via ``especifico.decorators.response.ResponseValidator``, if you want to change
the validation, you can override the default class with:

.. code-block:: python

    validator_map = {
        'response': CustomResponseValidator
    }
    app = especifico.FlaskApp(__name__)
    app.add_api('api.yaml', ..., validator_map=validator_map)


Error Handling
--------------
By default especifico error messages are JSON serialized according to
`Problem Details for HTTP APIs`_

Application can return errors using ``especifico.problem``.

.. _Problem Details for HTTP APIs: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
