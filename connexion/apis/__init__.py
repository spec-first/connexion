from .abstract import AbstractAPI

try:
    from .flask_api import FlaskApi
except ImportError as e:
    import sys
    import six
    import functools

    def _required_lib(exec_info, *args, **kwargs):
        six.reraise(*exec_info)

    FlaskApi = functools.partial(_required_lib, sys.exc_info())


__all__ = ['AbstractAPI', 'FlaskApi']
