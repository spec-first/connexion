Security
========

OAuth 2 Authentication and Authorization
----------------------------------------

Connexion supports one of the three OAuth 2 handling methods. (See
"TODO" below.) With Connexion, the API security definition **must**
include a 'x-tokenInfoUrl' (or set ``TOKENINFO_URL`` env var) with the
URL to validate and get the `token information`_. Connexion expects to
receive the OAuth token in the ``Authorization`` header field in the
format described in `RFC 6750 <rfc6750_>`_ section 2.1. This aspect
represents a significant difference from the usual OAuth flow.

HTTPS Support
-------------

When specifying HTTPS as the scheme in the API YAML file, all the URIs
in the served Swagger UI are HTTPS endpoints. The problem: The default
server that runs is a "normal" HTTP server. This means that the
Swagger UI cannot be used to play with the API. What is the correct
way to start a HTTPS server when using Connexion?

.. _rfc6750: https://tools.ietf.org/html/rfc6750
.. _swager.spec.security_definition: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object
.. _swager.spec.security_requirement: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-requirement-object
.. _token information: https://tools.ietf.org/html/rfc6749
