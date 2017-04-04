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
except ImportError as e:  # pragma: no cover
    import sys
    import six
    import functools

    def _required_lib(exec_info, *args, **kwargs):
        six.reraise(*exec_info)

    FlaskApi = functools.partial(_required_lib, sys.exc_info())
    FlaskApp = functools.partial(_required_lib, sys.exc_info())

App = FlaskApp
Api = FlaskApi

# This version is replaced during release process.
__version__ = '2016.0.dev1'
