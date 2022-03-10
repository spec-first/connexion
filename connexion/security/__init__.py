"""
This module defines SecurityHandlerFactories which support the creation of security
handlers for operations.

isort:skip_file
"""

# abstract
from .security_handler_factory import AbstractSecurityHandlerFactory  # NOQA

from ..utils import not_installed_error

# concrete
try:
    from .sync_security_handler_factory import SyncSecurityHandlerFactory
except ImportError as err:  # pragma: no cover
    SyncSecurityHandlerFactory = not_installed_error(err)

try:
    from .async_security_handler_factory import AsyncSecurityHandlerFactory
except ImportError as err:  # pragma: no cover
    AsyncSecurityHandlerFactory = not_installed_error(err)
