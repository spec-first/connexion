.. Connexion documentation master file, created by
   sphinx-quickstart on Wed Jun 17 12:09:55 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Connexion's documentation!
=====================================

Connexion is a framework on top of Flask_ that automagically handles
HTTP requests defined using `OpenAPI`_ (formerly known
as Swagger), supporting both `v2.0`_ and `v3.0`_ of the specification. 

Connexion allows you to write these specifications, then maps the
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
   v3

.. _Flask: http://flask.pocoo.org/
.. _OpenAPI: https://openapis.org/
.. _v2.0: https://spec.openapis.org/oas/v2.0.html
.. _v3.0: https://spec.openapis.org/oas/v3.0.1.html
