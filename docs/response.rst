Response Handling
=================

Response Serialization
----------------------
If the endpoint returns a Response object this response will be used as is.

Otherwise, and by default and if the specification defines that a endpoint
produces only json, connexion will automatically serialize the return value
for you and set the right content type in the HTTP header.

If the endpoint produces a single non json mimetype then connexion will
automatically set the right content type in the HTTP header.

Status codes
------------


Response Validation
-------------------

Error Handling
--------------
By default connexion error messages are JSON serialized according to
`Problem Details for HTTP APIs <http_problem_>`_.

Application can return errors using ``connexion.problem``.

.. _http_problem: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
