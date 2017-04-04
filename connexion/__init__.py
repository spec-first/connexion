import werkzeug.exceptions as exceptions  # NOQA
from .apps import AbstractApp, FlaskApp  # NOQA
from .apis import AbstractAPI, FlaskApi  # NOQA
from .exceptions import ProblemException  # NOQA
from .problem import problem  # NOQA
from .decorators.produces import NoContent  # NOQA
from .resolver import Resolution, Resolver, RestyResolver  # NOQA

App = FlaskApp
Api = FlaskApi

# This version is replaced during release process.
__version__ = '2016.0.dev1'
