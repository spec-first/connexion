.. raw:: html

   <a id="top"></a>
   <p align="center">
       <img src="docs/images/logo_banner.svg" width="100%"/>
   </p>
   <p align="center">
       <a href="https://pypi.org/project/connexion"><img alt="coveralls" src="https://img.shields.io/pypi/status/connexion.svg?style=flat-square&color=brightgreen"></a>
       <a href="https://pypi.org/project/connexion"><img alt="PyPI version" src="https://img.shields.io/pypi/v/connexion?color=brightgreen&style=flat-square"></a>
       <a href="https://github.com/spec-first/connexion/blob/feature/update-readme/LICENSE.txt"><img alt="License" src="https://img.shields.io/pypi/l/connexion?style=flat-square&color=brightgreen"></a>
       <a href="https://github.com/spec-first/connexion/actions/workflows/pipeline.yml"><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/spec-first/connexion/pipeline.yml?style=flat-square"></a>
       <a href="https://coveralls.io/github/ml6team/fondant?branch=main"><img alt="Coveralls" src="https://img.shields.io/coverallsCoverage/github/spec-first/connexion?style=flat-square"></a>
       <br>
       <br>
       <a href="https://connexion.readthedocs.io/en/stable/"><strong>Explore the docs »</strong></a>
   </p>

----

Connexion is a modern Python web framework that makes spec-first and api-first development easy.
You describe your API in an `OpenAPI`_ (or `Swagger`_) specification with as much detail as you
want and Connexion will guarantee that it works as you specified.

It works either standalone, or in combination with any ASGI or WSGI-compatible framework!

.. raw:: html

   <p align="center">
       <br>
       <a href="https://connexion.readthedocs.io/en/latest/v3.html"><strong>📢 Connexion 3 was recently released! Read about the changes here »</strong></a>
       <br>
       <br>
   </p>


Features
========

Connexion provides the following functionality **based on your specification**:

- **Automatic route registration**, no ``@route`` decorators needed
- **Authentication**, split from your application logic
- **Request and response validation** of headers, parameters, and body
- **Parameter parsing and injection**, no request object needed
- **Response serialization**, you can return regular Python objects
- **A Swagger UI console** with live documentation and ‘try it out’ feature
- **Pluggability**, in all dimensions

Connexion also **helps you write your OpenAPI specification** and develop against it by providing a command line interface which lets you test and mock your specification.

.. code-block:: bash

   connexion run openapi.yaml

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Why Connexion
=============

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
they often end up lacking details or mix your documentation with the implementation
logic of your application.

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

How to Use
==========

Installation
------------

You can install connexion using pip:

.. code-block:: bash

    $ pip install connexion

Connexion provides 'extras' with optional dependencies to unlock additional features:

- ``swagger-ui``: Enables a Swagger UI console for your application.
- ``uvicorn``: Enables to run the your application using :code:`app.run()` for
  development instead of using an external ASGI server.
- ``flask``: Enables the ``FlaskApp`` to build applications compatible with the Flask
  ecosystem.

You can install them as follows:

.. code-block:: bash

    $ pip install connexion[swagger-ui]
    $ pip install connexion[swagger-ui,uvicorn].

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>


Creating your application
-------------------------

Connexion can be used either as a standalone application or as a middleware wrapping an existing
ASGI (or WSGI) application written using a different framework. The standalone application can be
built using either the :code:`AsyncApp` or :code:`FlaskApp`.

- The :code:`AsyncApp` is a lightweight application with native asynchronous support. Use it if you
  are starting a new project and have no specific reason to use one of the other options.

  .. code-block:: python

      from connexion import AsyncApp

      app = AsyncApp(__name__)

- The :code:`FlaskApp` leverages the `Flask` framework, which is useful if you're migrating from
  connexion 2.X or you want to leverage the `Flask` ecosystem.

  .. code-block:: python

      from connexion import FlaskApp

      app = FlaskApp(__name__)

- The :code:`ConnexionMiddleware` can be wrapped around any existing ASGI or WSGI application.
  Use it if you already have an application written in a different framework and want to add
  functionality provided by connexion

  .. code-block:: python

      from asgi_framework import App
      from connexion import ConnexionMiddleware

      app = App(__name__)
      app = ConnexionMiddleware(app)

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Registering an API
------------------

While you can register individual routes on your application, Connexion really shines when you
register an API defined by an OpenAPI (or Swagger) specification.
The operation described in your specification is automatically linked to your Python view function via the ``operationId``

**run.py**

.. code-block:: python

   def post_greeting(name: str, greeting: str):  # Paramaeters are automatically unpacked
       return f"{greeting} {name}", 200          # Responses are automatically serialized

   app.add_api("openapi.yaml")

**openapi.yaml**

.. code-block:: yaml

   ...
   paths:
     /greeting/{name}:
       post:
         operationId: run.post_greeting
         responses:
           200:
             content:
               text/plain:
                 schema:
                   type: string
         parameters:
           - name: name
             in: path
             required: true
             schema:
               type: string
           - name: greeting
             in: query
             required: true
             schema:
               type: string

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Running your application
------------------------

If you installed connexion using :code:`connexion[uvicorn]`, you can run it using the
:code:`run` method. This is only recommended for development:

.. code-block:: python

    app.run()

In production, run your application using an ASGI server such as `uvicorn`. If you defined your
:code:`app` in a python module called :code:`run.py`, you can run it as follows:

.. code-block:: bash

    $ uvicorn run:app

Or with gunicorn:

.. code-block:: bash

    $ gunicorn -k uvicorn.workers.UvicornWorker run:app

----

Now you're able to run and use Connexion!

See the `examples`_ folder for more examples.

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Thanks
======

We'd like to thank all of Connexion's contributors for working on this
project, Swagger/OpenAPI for their support, and Zalando for originally developing and releasing Connexion.

Sponsors
--------

.. image:: ./docs/images/sponsors/ML6.png
   :alt: GitHub Sponsors
   :target: https://www.ml6.eu

|
Sponsors help us dedicate time to maintain Connexion. Want to help?

.. raw:: html

   <a href="https://github.com/sponsors/spec-first"><strong>Explore the options »</strong></a>

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Changes
=======

A full changelog is maintained on the `GitHub releases page`_.

.. _GitHub releases page: https://github.com/spec-first/connexion/releases

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Contributing
============

We welcome your ideas, issues, and pull requests. Just follow the
usual/standard GitHub practices.

For easy development, install connexion using poetry with all extras, and
install the pre-commit hooks to automatically run black formatting and static analysis checks.

.. code-block:: bash

    pip install poetry
    poetry install --all-extras
    pre-commit install

You can find out more about how Connexion works and where to apply your changes by having a look
at our `ARCHITECTURE.rst <ARCHITECTURE.rst>`_.

Unless you explicitly state otherwise in advance, any non trivial
contribution intentionally submitted for inclusion in this project by you
to the steward of this repository shall be under the
terms and conditions of Apache License 2.0 written below, without any
additional copyright information, terms or conditions.

.. raw:: html

   <p align="right">(<a href="#top">back to top</a>)</p>

Recommended Resources
---------------------

About the advantages of working spec-first:

* `Blog Atlassian`_
* `API guidelines Zalando`_
* `Blog ML6`_
* `Blog Zalando`_

Tools to help you work spec-first:

* `Online swagger editor`_
* `VS Code plugin`_
* `Pycharm plugin`_

.. _v3 documentation: https://connexion.readthedocs.io/en/latest/v3.html
.. _OpenAPI: https://openapis.org/
.. _Swagger: http://swagger.io/open-source-integrations/
.. _Blog atlassian: https://www.atlassian.com/blog/technology/spec-first-api-development
.. _Blog ML6: https://blog.ml6.eu/why-we-decided-to-help-maintain-connexion-c9f449877083
.. _Blog Zalando: https://engineering.zalando.com/posts/2016/12/crafting-effective-microservices-in-python.html
.. _API guidelines Zalando: https://opensource.zalando.com/restful-api-guidelines/#api-first
.. _Online swagger editor: https://editor.swagger.io/
.. _VS Code plugin: https://marketplace.visualstudio.com/items?itemName=42Crunch.vscode-openapi
.. _Pycharm plugin: https://plugins.jetbrains.com/plugin/14837-openapi-swagger-editor
.. _examples: ./examples
