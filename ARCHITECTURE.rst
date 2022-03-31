Architecture
============

This document describes the high-level architecture of Específico.

.. image:: docs/images/architecture.png
  :width: 800
  :align: center
  :alt: Específico architecture

Apps
----

A Específico ``App`` or application wraps a specific framework application (currently Flask or
AioHttp) and exposes a standardized interface for users to create and configure their Específico
application.

While a Específico app implements the WSGI interface, it only acts ass a pass-through and doesn't
actually intercept requests and responses. Específico does all request and response manipulation
by wrapping the user view function in a Específico ``Operation``. The underlying framework
application handles incoming requests and routes them to the correct Específico ``Operation``.

Api
---

An especifico ``API`` takes in an OpenAPI specification and translates the operations defined in it to
a set of Específico ``Operations``. This set of operations is implemented as a framework blueprint
(A `Flask blueprint`_ or framework-specific equivalent), which can be registered on the framework
application.

For each operation, the ``API`` resolves the user view function to link to the operation, wraps it
with a Específico ``Operation`` which it configures based on the OpenAPI spec, and finally adds it as
a route on the framework blueprint.

When the ``API`` is registered on the Específico ``APP``, the underlying framework blueprint is
registered on the framework app.

Operations
----------

A Específico ``Operation`` implements an OpenAPI operation (`swagger 2`_, `OpenAPI 3`_), which
describes a single API operation on a path. It wraps the view function linked to the operation with
decorators to handle security, validation, serialization etc. based on the OpenAPI specification,
and exposes the result to be registered as a route on the application.

These decorators intercept incoming requests and outgoing responses of the operation and allow
Específico to manipulate them while leaving the routing up to the underlying framework. The split
into separate decorators allows for a clean layered implementation of Específico functionality.

The result is equivalent to the following user code, but instead Específico implements this
automatically based on the OpenAPI spec.

.. code-block:: python

    @request_response_lifecycle
    @secure_endpoint
    @validate_inputs
    @deserialize_function_inputs
    @serialize_function_outputs
    @validate_outputs
    def user_provided_view_function():
        ...


Específico requests and responses
--------------------------------

Específico defines a request and response interface for internal use. The outermost decorator of
the operation casts framework specific requests to ``EspecíficoRequests`` and ``EspecíficoResponses``
to framework specific responses.

.. _Flask blueprint: https://flask.palletsprojects.com/en/2.0.x/blueprints/
.. _swagger 2: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#operation-object
.. _OpenAPI 3: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.0.md#operationObject
