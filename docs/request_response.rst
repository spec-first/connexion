Request Handling
================
Connexion validates incoming requests for conformance with the schemas
described in swagger specification.

Request parameters will be provided to the handler functions as keyword
arguments if they are included in the function's signature, otherwise body
parameters can be accessed from ``connexion.request.json`` and query parameters
can be accessed from ``connexion.request.args``.


Response Serialization
----------------------
By default and if the specification defines that a endpoint produces only json,
connexion will automatically serialize the return value for you and set the
right content type in the HTTP header.

If the endpoint produces a single non json mimetype then connexion will
automatically set the right content type in the HTTP header.


Error Handling
--------------
By default connexion error messages are JSON serialized according to
`Problem Details for HTTP APIs <http_problem_>`_.

Application can return errors using ``connexion.problem``.

.. _http_problem: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
