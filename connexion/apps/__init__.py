from .abstract import AbstractApp

try:
    from .flask_app import FlaskApp
except ImportError as e:
    import sys
    import six
    import functools

    def _required_lib(exec_info, *args, **kwargs):
        six.reraise(*exec_info)

    FlaskApp = functools.partial(_required_lib, sys.exc_info())


__all__ = ['AbstractApp', 'FlaskApp']
