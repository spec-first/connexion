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
REST API in as much detail as you want; Connexion then guarantees that it will work as you
specified.

Connexion was built this way in order to:

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

If multiple teams depend on your APIs, you can use Connexion to easily
send them the documentation of your API. This guarantees that your API will
follow the specification that you wrote. This is a different process from 
the one offered by most frameworks, which generate a specification
*after* you've written the code.
Some disadvantages of generating specifications based on code is that
they often end up lacking details or mix your documentation with the code
logic of your application.

Other Sources/Mentions
----------------------

- Zalando RESTful API guidelines with `API First`_
- Connexion listed on Swagger_'s website
- Blog post: `Crafting effective Microservices in Python`_

New in Connexion 3.0:
---------------------

- Connexion can now be used as middleware to supercharge any ASGI or WSGI compatible framework.
- Aiohttp support has been dropped in favor of an ASGI compatible ``AsyncApp`` built on top of Starlette.
- Connexion functionality is now pluggable by adding or removing middleware.
- Validation is now pluggable by content type, solving longstanding issues regarding endpoints with
  multiple content types and providing a pluggable interface.

For more detailed information on the changes in 3.0, see the `v3 documentation`_.

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

.. _API First: https://opensource.zalando.com/restful-api-guidelines/#api-first
.. _Hug: https://github.com/timothycrosley/hug
.. _Swagger: http://swagger.io/open-source-integrations/
.. _OpenAPI Specification: https://www.openapis.org/
.. _OpenAPI 3.0 Style Values: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#style-values
.. _Operation Object: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
.. _swager.spec.security_definition: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object
.. _swager.spec.security_requirement: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-requirement-object
.. _YAML format: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#format
.. _Connexion's Documentation Page: http://connexion.readthedocs.org/en/latest/
.. _Crafting effective Microservices in Python: https://jobs.zalando.com/tech/blog/crafting-effective-microservices-in-python/
.. _issues where we are looking for contributions: https://github.com/spec-first/connexion/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22
.. _v3 documentation: ./docs/v3.rst
