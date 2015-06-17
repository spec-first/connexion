Security
========

Authentication and Authorization
--------------------------------
If the specification includes a Oauth2 `Security Definition <swager.spec.security_definition_>`_ compatible with the
Zalando Greendale Team's infrastructure connexion will automatically handle token validation and authorization for
operations that have `Security Requirements <swager.spec.security_requirement_>`_. One main difference between the usual
Oauth flow and the one connexion uses is that the API Security Definition **must** include a 'x-tokenInfoUrl' with the
url to use to validate and get the token information.
Connexion expects to receive the Oauth token in the ``Authorization`` header field in the format described in
`RFC 6750 <rfc6750_>`_ section 2.1.

.. _rfc6750: https://tools.ietf.org/html/rfc6750
.. _swager.spec.security_definition: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object
.. _swager.spec.security_requirement: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-requirement-object
