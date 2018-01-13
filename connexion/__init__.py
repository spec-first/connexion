import werkzeug.exceptions as exceptions  # NOQA
from .apps import AbstractApp  # NOQA
from .apis import AbstractAPI  # NOQA
from .exceptions import ProblemException  # NOQA
from .problem import problem  # NOQA
from .decorators.produces import NoContent  # NOQA
from .resolver import Resolution, Resolver, RestyResolver  # NOQA

try:
    from .apis.flask_api import FlaskApi
    from .apps.flask_app import FlaskApp
    from flask import request  # NOQA
except ImportError as e:  # pragma: no cover
    import sys
    import six
    import functools

    def _required_lib(exec_info, *args, **kwargs):
        six.reraise(*exec_info)

    _flask_not_installed_error = functools.partial(_required_lib, sys.exc_info())

    FlaskApi = _flask_not_installed_error
    FlaskApp = _flask_not_installed_error

App = FlaskApp
Api = FlaskApi

# This version is replaced during release process.
__version__ = '2018.0.dev1'
