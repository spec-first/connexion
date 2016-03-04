Request Handling
================
Connexion validates incoming requests for conformance with the schemas
described in swagger specification.

Request parameters will be provided to the handler functions as keyword
arguments if they are included in the function's signature, otherwise body
parameters can be accessed from ``connexion.request.json`` and query parameters
can be accessed from ``connexion.request.args``.

Request Validation
------------------
Both the request body and parameters are validated against the specification,
using `jsonschema`_.

If the request doesn't match the specification connexion will return a 400
error.

Request Parameters
------------------
URL and FormData parameters are passed to the view function as arguments if the
function signature allows that argument to be received.

The body parameter is passed to the view function as an argument with the name
used in the specification if the function signature allows that argument to
be received.

Connexion will also use default values if they are provided.

.. _jsonschema: https://pypi.python.org/pypi/jsonschema