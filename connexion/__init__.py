"""
Connexion is a framework that automagically handles HTTP requests based on OpenAPI Specification
(formerly known as Swagger Spec) of your API described in YAML format. Connexion allows you to
write an OpenAPI specification, then maps the endpoints to your Python functions; this makes it
unique, as many tools generate the specification based on your Python code. You can describe your
REST API in as much detail as you want; then Connexion guarantees that it will work as you
specified.
"""

from .apps import AbstractApp  # NOQA
from .apps.asynchronous import AsyncApp
from .datastructures import NoContent  # NOQA
from .exceptions import ProblemException  # NOQA
from .problem import problem  # NOQA
from .resolver import Resolution, Resolver, RestyResolver  # NOQA
from .utils import not_installed_error  # NOQA

try:
    from connexion.apps.flask import FlaskApi, FlaskApp
except ImportError as e:  # pragma: no cover
    _flask_not_installed_error = not_installed_error(
        e, msg="Please install connexion using the 'flask' extra"
    )
    FlaskApi = _flask_not_installed_error  # type: ignore
    FlaskApp = _flask_not_installed_error  # type: ignore

from connexion.apps.asynchronous import AsyncApi, AsyncApp
from connexion.context import request
from connexion.middleware import ConnexionMiddleware

App = FlaskApp
Api = FlaskApi
