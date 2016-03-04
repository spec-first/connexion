Request Handling
================
Connexion validates incoming requests for conformance with the schemas
described in swagger specification.

Request parameters will be provided to the handler functions as keyword
arguments if they are included in the function's signature, otherwise body
parameters can be accessed from ``connexion.request.json`` and query parameters
can be accessed from ``connexion.request.args``.