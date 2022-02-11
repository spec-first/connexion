"""
Connexion is a framework that automagically handles HTTP requests based on OpenAPI Specification
(formerly known as Swagger Spec) of your API described in YAML format. Connexion allows you to
write an OpenAPI specification, then maps the endpoints to your Python functions; this makes it
unique, as many tools generate the specification based on your Python code. You can describe your
REST API in as much detail as you want; then Connexion guarantees that it will work as you
specified.
"""

import sys

import werkzeug.exceptions as exceptions  # NOQA

from .apis import AbstractAPI  # NOQA
from .apps import AbstractApp  # NOQA
from .decorators.produces import NoContent  # NOQA
from .exceptions import ProblemException  # NOQA
# add operation for backwards compatibility
from .operations import compat
from .problem import problem  # NOQA
from .resolver import Resolution, Resolver, RestyResolver  # NOQA
from .utils import not_installed_error  # NOQA

full_name = f'{__package__}.operation'
sys.modules[full_name] = sys.modules[compat.__name__]


try:
    from flask import request  # NOQA

    from .apis.flask_api import FlaskApi, context  # NOQA
    from .apps.flask_app import FlaskApp
except ImportError as e:  # pragma: no cover
    _flask_not_installed_error = not_installed_error(e)
    FlaskApi = _flask_not_installed_error
    FlaskApp = _flask_not_installed_error

App = FlaskApp
Api = FlaskApi

try:
    from .apis.aiohttp_api import AioHttpApi
    from .apps.aiohttp_app import AioHttpApp
except ImportError as e:  # pragma: no cover
    _aiohttp_not_installed_error = not_installed_error(e)
    AioHttpApi = _aiohttp_not_installed_error
    AioHttpApp = _aiohttp_not_installed_error

# This version is replaced during release process.
__version__ = '2020.0.dev1'
