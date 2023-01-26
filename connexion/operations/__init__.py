"""
This module defines Connexion Operation classes. A Connexion Operation implements an OpenAPI
operation, which describes a single API operation on a path. It wraps the view function linked to
the operation with decorators to handle security, validation, serialization etc. based on the
OpenAPI specification, and exposes the result to be registered as a route on the application.

"""

from .abstract import AbstractOperation  # noqa
from .openapi import OpenAPIOperation  # noqa
from .swagger2 import Swagger2Operation  # noqa
