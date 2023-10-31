Connexion
=========

.. image:: https://github.com/spec-first/connexion/actions/workflows/pipeline.yml/badge.svg
   :alt: Build status
   :target: https://github.com/spec-first/connexion/actions/workflows/pipeline.yml

.. image:: https://coveralls.io/repos/github/spec-first/connexion/badge.svg?branch=main
   :target: https://coveralls.io/github/spec-first/connexion?branch=main
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
   :target: https://github.com/spec-first/connexion/blob/main/LICENSE.txt
   :alt: License

Connexion is a framework that automagically handles HTTP requests based on `OpenAPI Specification`_
(formerly known as Swagger Spec) of your API described in `YAML format`_. Connexion allows you to
write an OpenAPI specification, then maps the endpoints to your Python functions; this makes it
unique, as many tools generate the specification based on your Python code. You can describe your
REST API in as much detail as you want; then Connexion guarantees that it will work as you
specified.

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

- Zalando RESTful API guidelines with `API First`_
- Connexion listed on Swagger_'s website
- Blog post: `Crafting effective Microservices in Python`_

New in Connexion 2.0:
---------------------
- App and Api options must be provided through the "options" argument (``old_style_options`` have been removed).
- You must specify a form content-type in 'consumes' in order to consume form data.
- The `Operation` interface has been formalized in the `AbstractOperation` class.
- The `Operation` class has been renamed to `Swagger2Operation`.
- Array parameter deserialization now follows the Swagger 2.0 spec more closely.
  In situations when a query parameter is passed multiple times, and the collectionFormat is either csv or pipes, the right-most value will be used.
  For example, `?q=1,2,3&q=4,5,6` will result in `q = [4, 5, 6]`.
  The old behavior is available by setting the collectionFormat to `multi`, or by importing `decorators.uri_parsing.AlwaysMultiURIParser` and passing `parser_class=AlwaysMultiURIParser` to your Api.
- The spec validator library has changed from `swagger-spec-validator` to `openapi-spec-validator`.
- Errors that previously raised `SwaggerValidationError` now raise the `InvalidSpecification` exception.
  All spec validation errors should be wrapped with `InvalidSpecification`.
- Support for nullable/x-nullable, readOnly and writeOnly/x-writeOnly has been added to the standard json schema validator.
- Custom validators can now be specified on api level (instead of app level).
- Added support for basic authentication and apikey authentication
- If unsupported security requirements are defined or ``x-tokenInfoFunc``/``x-tokenInfoUrl`` is missing, connexion now denies requests instead of allowing access without security-check.
- Accessing ``connexion.request.user`` / ``flask.request.user`` is no longer supported, use ``connexion.context['user']`` instead

How to Use
==========

Prerequisites
-------------

Python 3.8+

Installing It
-------------

In your command line, type:

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

See the `examples`_ folder for some small examples.

Now you're able to run and use Connexion!

Documentation
=============
Additional information is available at `Connexion's Documentation Page`_.

Changes
=======

A full changelog is maintained on the `GitHub releases page`_.

.. _GitHub releases page: https://github.com/spec-first/connexion/releases

Contributing to Connexion/TODOs
===============================

We welcome your ideas, issues, and pull requests. Just follow the
usual/standard GitHub practices.

For easy development, install connexion using poetry with all extras, and
install the pre-commit hooks to automatically run black formatting and static analysis checks.

.. code-block:: bash

    poetry install --all-extras
    pre-commit install

You can find out more about how Connexion works and where to apply your changes by having a look
at our `ARCHITECTURE.rst <ARCHITECTURE.rst>`_.

Unless you explicitly state otherwise in advance, any non trivial
contribution intentionally submitted for inclusion in this project by you
to the steward of this repository shall be under the
terms and conditions of Apache License 2.0 written below, without any
additional copyright information, terms or conditions.

TODOs
-----


If you'd like to become a more consistent contributor to Connexion, we'd love your help working on
these we have a list of `issues where we are looking for contributions`_.

Thanks
===================

We'd like to thank all of Connexion's contributors for working on this
project, and to Swagger/OpenAPI for their support.

.. _Flask: http://flask.pocoo.org/
.. _API First: https://opensource.zalando.com/restful-api-guidelines/#api-first
.. _Hug: https://github.com/timothycrosley/hug
.. _Swagger: http://swagger.io/open-source-integrations/
.. _Jinja2: http://jinja.pocoo.org/
.. _rfc6750: https://tools.ietf.org/html/rfc6750
.. _OpenAPI Specification: https://www.openapis.org/
.. _OpenAPI 3.0 Style Values: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#style-values
.. _Operation Object: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _swager.spec.security_definition: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object
.. _swager.spec.security_requirement: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-requirement-object
.. _YAML format: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#format
.. _token information: https://tools.ietf.org/html/rfc6749
.. _Tornado: http://www.tornadoweb.org/en/stable/
.. _described by Flask: http://flask.pocoo.org/snippets/111/
.. _werkzeug: http://werkzeug.pocoo.org/
.. _Connexion's Documentation Page: http://connexion.readthedocs.org/en/latest/
.. _Crafting effective Microservices in Python: https://jobs.zalando.com/tech/blog/crafting-effective-microservices-in-python/
.. _issues where we are looking for contributions: https://github.com/zalando/connexion/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22
.. _HTTP Methods work in Flask: http://flask.pocoo.org/docs/1.0/quickstart/#http-methods
