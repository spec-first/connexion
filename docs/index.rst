.. Connexion documentation master file, created by
   sphinx-quickstart on Wed Jun 17 12:09:55 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Connexion's documentation!
=====================================

Connexion is a framework on top of Flask_ that automagically handles
HTTP requests based on either the `OpenAPI 2.0 Specification`_ (formerly known
as Swagger Spec) or the `OpenAPI 3.0 Specification`_. Connexion
allows you to write a Swagger specification and then maps the
endpoints to your Python functions. This is what makes it unique from
other tools that generate the specification based on your Python
code. You are free to describe your REST API with as much detail as
you want and then Connexion guarantees that it will work as
you specified. We built Connexion this way in order to:

- Simplify the development process
- Reduce misinterpretation about what an API is going to look like

Contents:

.. toctree::
   :maxdepth: 2

   quickstart
   cli
   routing
   request
   response
   security
   cookbook
   exceptions

.. _Flask: http://flask.pocoo.org/
.. _OpenAPI 2.0 Specification: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md
.. _OpenAPI 3.0 Specification: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md
