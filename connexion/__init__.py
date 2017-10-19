import werkzeug.exceptions as exceptions  # NOQA
from .apps import AbstractApp  # NOQA
from .apis import AbstractAPI  # NOQA
from .exceptions import ProblemException  # NOQA
from .problem import problem  # NOQA
from .decorators.produces import NoContent  # NOQA
from .resolver import Resolution, Resolver, RestyResolver  # NOQA

import sys

try:
    from .apis.flask_api import FlaskApi
    from .apps.flask_app import FlaskApp
    from flask import request  # NOQA
except ImportError as e:  # pragma: no cover
    import six
    import functools

    def _required_lib(exec_info, *args, **kwargs):
        six.reraise(*exec_info)

    _flask_not_installed_error = functools.partial(_required_lib, sys.exc_info())

    FlaskApi = _flask_not_installed_error
    FlaskApp = _flask_not_installed_error

App = FlaskApp
Api = FlaskApi

if sys.version_info[0:2] >= (3, 4): # pragma: no cover
    try:
        from .apis.aiohttp_api import AioHttpApi
        from .apps.aiohttp_app import AioHttpApp
    except ImportError as e:
        import six
        import functools

        def _required_lib(exec_info, *args, **kwargs):
            six.reraise(*exec_info)

        _aiohttp_not_installed_error = functools.partial(_required_lib, sys.exc_info())

        AioHttpApi = _aiohttp_not_installed_error
        AioHttpApp = _aiohttp_not_installed_error

# This version is replaced during release process.
__version__ = '2018.0.dev1'
