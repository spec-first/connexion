Security
========

OAuth 2 Authentication and Authorization
----------------------------------------

Connexion supports one of the three OAuth 2 handling methods. (See
"TODO" below.) With Connexion, the API security definition **must**
include a 'x-tokenInfoUrl' or 'x-tokenInfoFunc (or set ``TOKENINFO_URL``
or ``TOKENINFO_FUNC`` env var respectively). 

If 'x-tokenInfoFunc' is used, it must contain a reference to a function 
used to obtain the token info. This reference should be a string using
the same syntax that is used to connect an ``operationId`` to a Python
function when routing. For example, an ``x-tokenInfoFunc`` of 
``auth.verifyToken`` would pass the user's token string to the function
``verifyToken`` in the module ``auth.py``. The referenced function should 
return a dict containing a ``scope`` or ``scopes`` field that is either 
a space-separated list or an array of scopes belonging to the supplied 
token. This list of scopes will be validated against the scopes required
by the API security definition to determine if the user is authorized.

If 'x-tokenInfoUrl' is used, it must contain a URL to validate and get
the token information which complies with `RFC 6749 <rfc6749_>`_.

When both 'x-tokenInfoUrl' and 'x-tokenInfoFunc' are used, Connexion 
will prioritize the function method. Connexion expects to receive the 
OAuth token in the ``Authorization`` header field in the format 
described in `RFC 6750 <rfc6750_>`_ section 2.1. This aspect represents 
a significant difference from the usual OAuth flow.

The ``uid`` property (username) of the Token Info response will be passed in the ``user`` argument to the handler function.

You can find a `minimal OAuth example application`_ in Connexion's "examples" folder.

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
.. _rfc6749: https://tools.ietf.org/html/rfc6749
.. _minimal OAuth example application: https://github.com/zalando/connexion/tree/master/examples/oauth2
