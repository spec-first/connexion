"""
This module defines SecurityHandlerFactories which support the creation of security
handlers for operations.

isort:skip_file
"""

# abstract
from .async_security_handler_factory import AbstractAsyncSecurityHandlerFactory  # NOQA
from .security_handler_factory import AbstractSecurityHandlerFactory  # NOQA

from ..utils import not_installed_error

# concrete
try:
    from .flask_security_handler_factory import FlaskSecurityHandlerFactory
except ImportError as err:  # pragma: no cover
    FlaskSecurityHandlerFactory = not_installed_error(err)

try:
    from .aiohttp_security_handler_factory import AioHttpSecurityHandlerFactory
except ImportError as err:  # pragma: no cover
    AioHttpSecurityHandlerFactory = not_installed_error(err)
