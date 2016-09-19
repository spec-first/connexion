Connexion
=========

.. image:: https://badges.gitter.im/zalando/connexion.svg
   :alt: Join the chat at https://gitter.im/zalando/connexion
   :target: https://gitter.im/zalando/connexion?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

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

Connexion is a framework on top of Flask_ that automagically handles
HTTP requests based on `OpenAPI 2.0 Specification`_ (formerly known as
Swagger Spec) of your API described in `YAML format`_. Connexion
allows you to write a Swagger specification, then maps the
endpoints to your Python functions; this makes it unique, as many tools generate the specification based on your Python
code. You can describe your REST API in as much detail as
you want; then Connexion guarantees that it will work as
you specified.

We built Connexion this way in order to:

- simplify the development process
- confirm expectations about what your API will look like

Connexion Features:
-------------------

- Validates requests and endpoint parameters automatically, based on
  your specification
- Provides a Web Swagger Console UI so that the users of your API can
  have live documentation and even call your API's endpoints
  through it
- Handles OAuth 2 token-based authentication
- Supports API versioning
- Supports automatic serialization of payloads. If your
  specification defines that an endpoint returns JSON, Connexion will
  automatically serialize the return value for you and set the right
  content type in the HTTP header.

Why Connexion
-------------

With Connexion, you write the spec first. Connexion then calls your Python
code, handling the mapping from the specification to the code. This
incentivizes you to write the specification so that all of your
developers can understand what your API does, even before you write a
single line of code.

If multiple teams depend on your APIs, you can use Connexion to easily send them the documentation of your API. This guarantees that your API will follow the specification that you wrote. This is a different process from that offered by frameworks such as Hug_, which generates a specification *after* you've written the code. Some disadvantages of generating specifications based on code is that they often end up lacking details or mix your documentation with the code logic of your application.

Other Sources/Mentions
----------------------

- Zalando Tech blog post `API First`_
- Connexion listed on Swagger_'s website
- Blog post: `Crafting effective Microservices in Python`_

How to Use
==========

Prerequisites
-------------

Python 2.7 or Python 3.4+

Installing It
-------------

In your command line, type this:

.. code-block:: bash

    $ pip install connexion


Running It
----------

Place your API YAML inside a folder in the root
path of your application (e.g ``swagger/``). Then run:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml')
    app.run(port=8080)

See the `Connexion Pet Store Example Application`_ for a sample
specification.

Now you're able run and use Connexion!


OAuth 2 Authentication and Authorization
----------------------------------------

Connexion supports one of the three OAuth 2 handling methods. (See
"TODO" below.) With Connexion, the API security definition **must**
include a 'x-tokenInfoUrl' (or set ``TOKENINFO_URL`` env var) with the
URL to validate and get the `token information`_. Connexion expects to
receive the OAuth token in the ``Authorization`` header field, in the
format described in `RFC 6750 <rfc6750_>`_ section 2.1. This aspect
represents a significant difference from the usual OAuth flow.

Dynamic Rendering of Your Specification
---------------------------------------

Connexion uses Jinja2_ to allow specification parameterization through the `arguments` parameter. You can define specification arguments for the application either globally (via the `connexion.App` constructor) or for each specific API (via the `connexion.App#add_api` method):

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/',
                        arguments={'global': 'global_value'})
    app.add_api('my_api.yaml', arguments={'api_local': 'local_value'})
    app.run(port=8080)

When a value is provided both globally and on the API, the API value will take precedence.

Endpoint Routing to Your Python Views
-------------------------------------

Connexion uses the ``operationId`` from each `Operation Object`_ to
identify which Python function should handle each URL.

**Explicit Routing**:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

If you provide this path in your specification POST requests to
``http://MYHOST/hello_world``, it will be handled by the function
``hello_world`` in the ``myapp.api`` module. Optionally, you can include
``x-swagger-router-controller`` in your operation definition, making
``operationId`` relative:

.. code-block:: yaml

    paths:
      /hello_world:
        post:
          x-swagger-router-controller: myapp.api
          operationId: hello_world

Automatic Routing
-----------------

To customize this behavior, Connexion can use alternative
``Resolvers``--for example, ``RestyResolver``. The ``RestyResolver``
will compose an ``operationId`` based on the path and HTTP method of
the endpoints in your specification:

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

``RestyResolver`` will give precedence to any ``operationId`` encountered in the specification. It will also respect
``x-router-controller``. You can import and extend ``connexion.resolver.Resolver`` to implement your own ``operationId``
(and function) resolution algorithm.

Automatic Parameter Handling
----------------------------

Connexion automatically maps the parameters defined in your endpoint specification to arguments of your Python views as named parameters, and, whenever possible, with value casting. Simply define the endpoint's parameters with the same names as your views arguments.

As an example, say you have a endpoint specified as:

.. code-block:: yaml

    paths:
      /foo:
        get:
          operationId: api.foo_get
          parameters:
            - name: message
              description: Some message.
              in: query
              type: string
              required: true

And the view function:

.. code-block:: python

    # api.py file

    def foo_get(message):
        # do something
        return 'You send the message: {}'.format(message), 200

In this example, Connexion automatically recognizes that your view
function expects an argument named `message` and assigns the value
of the endpoint parameter `message` to your view function.

.. warning:: When you define a parameter at your endpoint as *not* required, and your Python view has
             a non-named argument, you will get a "missing positional argument" exception whenever you call this endpoint WITHOUT the parameter.

Type casting
^^^^^^^^^^^^

Whenever possible, Connexion will try to parse your argument values and
do type casting to related Python native values. The current
available type castings are:

+--------------+-------------+
| Swagger Type | Python Type |
+==============+=============+
| integer      | int         |
+--------------+-------------+
| string       | str         |
+--------------+-------------+
| number       | float       |
+--------------+-------------+
| boolean      | bool        |
+--------------+-------------+
| array        | list        |
+--------------+-------------+
| object       | dict        |
+--------------+-------------+

If you use the `array` type In the Swagger definition, you can define the
`collectionFormat` so that it won't be recognized. Connexion currently
supports collection formats "pipes" and "csv". The default format is "csv".

Parameter validation
^^^^^^^^^^^^^^^^^^^^

Connexion can apply strict parameter validation for query and form data
parameters.  When this is enabled, requests that include parameters not defined
in the swagger spec return a 400 error.  You can enable it when adding the API
to your application:

.. code-block:: python

    app.add_api('my_apy.yaml', strict_validation=True)

API Versioning and basePath
---------------------------

You can also define a ``basePath`` on the top level of the API
specification. This is useful for versioned APIs. To serve the
previous endpoint from ``http://MYHOST/1.0/hello_world``, type:

.. code-block:: yaml

    basePath: /1.0

    paths:
      /hello_world:
        post:
          operationId: myapp.api.hello_world

If you don't want to include the base path in your specification, you
can provide it when adding the API to your application:

.. code-block:: python

    app.add_api('my_api.yaml', base_path='/1.0')

Swagger JSON
------------
Connexion makes the OpenAPI/Swagger specification in JSON format
available from ``swagger.json`` in the base path of the API.

You can disable the Swagger JSON at the application level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/',
                        swagger_json=False)
    app.add_api('my_api.yaml')

You can also disable it at the API level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_json=False)

HTTPS Support
-------------

When specifying HTTPS as the scheme in the API YAML file, all the URIs
in the served Swagger UI are HTTPS endpoints. The problem: The default
server that runs is a "normal" HTTP server. This means that the
Swagger UI cannot be used to play with the API. What is the correct
way to start a HTTPS server when using Connexion?

One way, `described by Flask`_, looks like this:

.. code-block:: python

   from OpenSSL import SSL
   context = SSL.Context(SSL.SSLv23_METHOD)
   context.use_privatekey_file('yourserver.key')
   context.use_certificate_file('yourserver.crt')

   app.run(host='127.0.0.1', port='12344',
           debug=False/True, ssl_context=context)

However, Connexion doesn't provide an ssl_context parameter. This is
because Flask doesn't, either--but it uses `**kwargs` to send the
parameters to the underlying [werkzeug](http://werkzeug.pocoo.org/) server.

The Swagger UI Console
----------------------

The Swagger UI for an API is available, by default, in
``{base_path}/ui/`` where ``base_path`` is the base path of the API.

You can disable the Swagger UI at the application level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/',
                        swagger_ui=False)
    app.add_api('my_api.yaml')


You can also disable it at the API level:

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', swagger_ui=False)

Server Backend
--------------

Connexion uses the default Flask server. For asynchronous
applications, you can also use Tornado_ as the HTTP server. To do
this, set your server to ``tornado``:

.. code-block:: python

    import connexion

    app = connexion.App(__name__, specification_dir='swagger/')
    app.run(server='tornado', port=8080)

You can use the Flask WSGI app with any WSGI container, e.g. `using
Flask with uWSGI`_ (this is common):

.. code-block:: python

    app = connexion.App(__name__, specification_dir='swagger/')
    application = app.app # expose global WSGI application object

Set up and run the installation code:

.. code-block:: bash

    $ sudo pip3 install uwsgi
    $ uwsgi --http :8080 -w app -p 16  # use 16 worker processes

See the `uWSGI documentation`_ for more information.

.. _using Flask with uWSGI: http://flask.pocoo.org/docs/latest/deploying/uwsgi/
.. _uWSGI documentation: https://uwsgi-docs.readthedocs.org/

Documentation
=============
Additional information is available at `Connexion's Documentation Page`_.

Contributing to Connexion/TODOs
===============================

We welcome your ideas, issues, and pull requests. Just follow the
usual/standard GitHub practices.

TODOs
-----

If you'd like to become a more consistent contributor to Connexion,
we'd love your help working on these:

- Additional ways to handle OAuth 2 authentications
- Overriding default validation error message
- Documentation (Response handling, Passing arguments to functions, etc)

Check our `issues waffle board`_ for more info.

Thanks
===================

We'd like to thank all of Connexion's contributors for working on this
project, and to Swagger/OpenAPI for their support.

License
===================

Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

.. _Flask: http://flask.pocoo.org/
.. _issues waffle board: https://waffle.io/zalando/connexion
.. _API First: https://tech.zalando.com/blog/on-apis-and-the-zalando-api-guild/
.. _Hug: https://github.com/timothycrosley/hug
.. _Swagger: http://swagger.io/open-source-integrations/
.. _Jinja2: http://jinja.pocoo.org/
.. _rfc6750: https://tools.ietf.org/html/rfc6750
.. _OpenAPI 2.0 Specification: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md
.. _Operation Object: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _swager.spec.security_definition: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object
.. _swager.spec.security_requirement: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-requirement-object
.. _YAML format: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#format
.. _token information: https://tools.ietf.org/html/rfc6749
.. _Tornado: http://www.tornadoweb.org/en/stable/
.. _Connexion Pet Store Example Application: https://github.com/hjacobs/connexion-example
.. _described by Flask: http://flask.pocoo.org/snippets/111/
.. _Connexion's Documentation Page: http://connexion.readthedocs.org/en/latest/
.. _Crafting effective Microservices in Python: http://caricio.com/2016/09/16/crafting-effective-microservices-in-python/
