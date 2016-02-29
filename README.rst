Connexion
=========

.. image:: https://travis-ci.org/zalando/connexion.svg?branch=master
   :target: https://travis-ci.org/zalando/connexion
   :alt: Travis CI build status

.. image:: https://coveralls.io/repos/zalando/connexion/badge.svg?branch=master
   :target: https://coveralls.io/r/zalando/connexion?branch=master
   :alt: Coveralls status

.. image:: https://img.shields.io/pypi/v/connexion.svg
   :target: https://pypi.python.org/pypi/connexion
   :alt: Latest Version

.. image:: https://img.shields.io/pypi/status/connexion.svg
   :target: https://pypi.python.org/pypi/connexion
   :alt: Development Status

.. image:: https://img.shields.io/pypi/pyversions/connexion.svg
   :target: https://pypi.python.org/pypi/connexion
   :alt: Python Versions

.. image:: https://img.shields.io/pypi/l/connexion.svg
   :target: https://github.com/zalando/connexion/blob/master/LICENSE
   :alt: License

Connexion is a framework on top of Flask_ to automagically handle your REST API requests
based on `OpenAPI 2.0 Specification`_ (formerly known as Swagger Spec) files
in YAML.

How to use
----------

Put your API YAML inside a folder in the root path of your application (e.g ``swagger/``) and then do

.. code-block:: python

    import connexion

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml')
    app.run(port=8080)

See the `Connexion Pet Store Example Application`_ for details.

Parameterization
----------------
Connexion uses Jinja2_ to allow the parameterization of specifications.

The specification arguments can be defined globally for the application or for each specific API:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/', arguments={'global': 'global_value'})
    app.add_api('my_api.yaml', arguments={'api_local': 'local_value'})
    app.run(port=8080)

If a value is provided both globally and on the API then the API value will take precedence.


Endpoint Routing
----------------
Connexion uses the ``operationId`` from each `Operation Object`_  to identify which function
should handle each URL.

For example:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

If you provided this path in your specification POST requests to ``http://MYHOST/hello_world`` would be handled by the
function ``hello_world`` in ``myapp.api``. Optionally you can include ``x-swagger-router-controller`` in your operation definition, making ``operationId`` relative:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          x-swagger-router-controller: myapp.api
          operationId: hello_world


To customize this behavior, Connexion can use alternative ``Resolvers``, for example ``RestyResolver``. The ``RestyResolver`` will compose an ``operationId`` based on the path and HTTP method of the endpoints in your specification:

.. code-block:: python

    from connexion.resolver import RestyResolver

    app = connexion.App(__name__)
    app.add_api('swagger.yaml', resolver=RestyResolver('api'))

.. code-block:: yaml

   paths:
     /:
       get:
          # Implied operationId: api.get
     /foo:
       get:
          # Implied operationId: api.foo.search
       post:
          # Implied operationId: api.foo.post

     '/foo/{id}':
       get:
          # Implied operationId: api.foo.get
       put:
          # Implied operationId: api.foo.post
       copy:
          # Implied operationId: api.foo.copy
       delete:
          # Implied operationId: api.foo.delete

``RestyResolver`` will give precedence to any ``operationId`` encountered in the specification. It will also respect ``x-router-controller``. You may import and extend ``connexion.resolver.Resolver`` to implement your own ``operationId`` (and function) resolution algorithm.

Additionally you can also define a ``basePath`` on the top level of the API specification, which is useful for versioned
APIs. If you wanted to serve the previous endpoint from  ``http://MYHOST/1.0/hello_world`` you could do:

.. code-block:: yaml

    basePath: /1.0

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

Other alternative if you don't want to include the base path in your specification is provide the base path when adding
the API to your application:

.. code-block:: python

    app.add_api('my_api.yaml', base_path='/1.0')

Response Serialization
----------------------
If the specification defines that a endpoint returns JSON, Connexion will automatically serialize the return value for
you and set the right content type in the HTTP header.

Authentication and Authorization
--------------------------------
If the specification includes a Oauth2 `Security Definition <swager.spec.security_definition_>`_ compatible with the
Zalando Greendale Team's infrastructure Connexion will automatically handle token validation and authorization for
operations that have `Security Requirements <swager.spec.security_requirement_>`_. One main difference between the usual
OAuth flow and the one Connexion uses is that the API Security Definition **must** include a 'x-tokenInfoUrl' (or set ``TOKENINFO_URL`` env var) with the
URL to use to validate and get the token information.
Connexion expects to receive the Oauth token in the ``Authorization`` header field in the format described in
`RFC 6750 <rfc6750_>`_ section 2.1.



Use your own security decorator
-------------------------------
Connexion adds a security decorator for each view function to handle (oauth) security. If you need your own security logic
like checking the token at your own endpoint and or setting a current user in your request context, you can create your own
security decorator and pass it to connexion at api creation time, like this

.. code-block:: python

    import my_module.security.decorators

    app.add_api('my_api.yaml',
                security_decorator = my_module.security.decorators.verify_oauth_at_my_way
                base_path='/1.0')



Look for example security decorators in `connexion.decorators.security`
A custom decorator may look like this:

.. code-block:: python

  """
  override the connexion security decorators
  """

  # Authentication and authorization related decorators

  from flask import request
  import functools
  import logging
  import requests
  from connexion import problem

  logger = logging.getLogger('connexion.api.custom_security')

  # use connection pool for OAuth tokeninfo
  adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
  session = requests.Session()
  session.mount('http://', adapter)
  session.mount('https://', adapter)



  def verify_oauth_at_my_way(allowed_scopes, function):
      """
      Special Decorator to verify oauth and set user and role(s)

      :param token_info_url: Url to get information about the token
      :type token_info_url: str
      :param allowed_scopes: Set with scopes that are allowed to access the endpoint
      :type allowed_scopes: set
      :type function: types.FunctionType
      :rtype: types.FunctionType
      """

      @functools.wraps(function)
      def wrapper(*args, **kwargs):
          logger.debug("%s MY SPECAL Oauth verification...", request.url)
          authorization = request.headers.get('Authorization')  # type: str
          if not authorization:
              logger.info("... No auth provided. Aborting with 401.")
              return problem(401, 'Unauthorized', "No authorization token provided")
          else:
              try:
                  _, token = authorization.split()  # type: str, str
              except ValueError:
                  return problem(401, 'Unauthorized', 'Invalid authorization header')

              session.headers['Authorization'] = authorization
              token_info_url = 'https://MY_OATH_SERVER/me'

              logger.debug("... Getting token '%s' from %s", token, token_info_url)

              token_request = session.get(token_info_url, timeout=15)

              logger.debug("... Token info (%d): %s", token_request.status_code, token_request.text)
              if not token_request.ok:
                  return problem(401, 'Unauthorized', "Provided oauth token is not valid")

              token_info = token_request.json()  # type: dict

              user_scopes = set(token_info['scope'])
              scopes_intersection = user_scopes & allowed_scopes
              logger.debug("... Scope intersection: %s", scopes_intersection)
              if not scopes_intersection:
                  logger.info("... User scopes (%s) don't include one of the allowed scopes (%s). Aborting with 401.",
                              user_scopes, allowed_scopes)
                  return problem(403, 'Forbidden', "Provided token doesn't have the required scope")
              logger.info("... Token authenticated.")

              # add the user info to the request context for later us in our view functions

              request.current_user_id = token_info.get('id') # just the user id
              request.current_user = token_info # the whole token

              # add your own logic here ....

          return function(*args, **kwargs)

      return wrapper


Swagger JSON
------------
Connexion makes the OpenAPI/Swagger specification in JSON format available from ``swagger.json`` in the base path of the API.

Swagger UI
----------
The Swagger UI for an API is available, by default, in ``{base_path}/ui/`` where ``base_path`` is the base path of the
API.

You can disable the Swagger UI either at application level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/', swagger_ui=False)
    app.add_api('my_api.yaml')


You can also disable it at API level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_ui=False)

Server Backend
--------------
By default Connexion uses the default Flask server but you can also use Tornado_ as the HTTP server, to do so set server
to ``tornado``:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, specification_dir='swagger/')
    app.run(server='tornado', port=8080)

You can use the Flask WSGI app with any WSGI container, e.g. `using Flask with uWSGI`_:

.. code-block:: python

    app = connexion.App(specification_dir='swagger/')
    application = app.app # expose global WSGI application object

.. code-block:: bash

    $ sudo pip3 install uwsgi
    $ uwsgi --http :8080 -w app -p 16  # use 16 worker processes

You can run uWSGI with a large number of worker processes to get high concurrency.

See the `uWSGI documentation`_ for more information.

.. _using Flask with uWSGI: http://flask.pocoo.org/docs/latest/deploying/uwsgi/
.. _uWSGI documentation: https://uwsgi-docs.readthedocs.org/

Releasing Connexion
===================

Build and upload new version to PyPI:

.. code-block:: bash

    $ ./release.sh <NEW-VERSION>

License
-------
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

.. _Flask: http://flask.pocoo.org/
.. _Jinja2: http://jinja.pocoo.org/
.. _rfc6750: https://tools.ietf.org/html/rfc6750
.. _OpenAPI 2.0 Specification: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md
.. _Operation Object: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _swager.spec.security_definition: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object
.. _swager.spec.security_requirement: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-requirement-object
.. _Tornado: http://www.tornadoweb.org/en/stable/
.. _Connexion Pet Store Example Application: https://github.com/hjacobs/connexion-example

