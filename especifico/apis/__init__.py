"""
This module defines Especifico APIs. A especifico API takes in an OpenAPI specification and
translates the operations defined in it to a set of Especifico Operations. This set of operations
is implemented as a framework blueprint (A Flask blueprint or framework-specific equivalent),
which can be registered on the framework application.

For each operation, the API resolves the user view function to link to the operation, wraps it
with a Especifico Operation which it configures based on the OpenAPI spec, and finally adds it as
a route on the framework blueprint.

When the API is registered on the Especifico APP, the underlying framework blueprint is registered
on the framework app.
"""


from .abstract import AbstractAPI  # NOQA
