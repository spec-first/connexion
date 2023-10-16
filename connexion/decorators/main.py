import abc
import asyncio
import functools
import json
import typing as t

from asgiref.sync import async_to_sync
from starlette.concurrency import run_in_threadpool

from connexion.context import operation, receive, scope
from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    BaseParameterDecorator,
    SyncParameterDecorator,
)
from connexion.decorators.response import (
    AsyncResponseDecorator,
    BaseResponseDecorator,
    NoResponseDecorator,
    SyncResponseDecorator,
)
from connexion.frameworks.abstract import Framework
from connexion.frameworks.starlette import Starlette as StarletteFramework
from connexion.uri_parsing import AbstractURIParser
from connexion.utils import not_installed_error

try:
    from connexion.frameworks.flask import Flask as FlaskFramework
except ImportError as e:
    _flask_not_installed_error = not_installed_error(
        e, msg="Please install connexion using the 'flask' extra"
    )
    FlaskFramework = _flask_not_installed_error  # type: ignore


class BaseDecorator:
    """Base class for connexion decorators."""

    framework: t.Type[Framework]

    def __init__(
        self,
        *,
        pythonic_params: bool = False,
        uri_parser_class: AbstractURIParser = None,
        jsonifier=json,
    ) -> None:
        self.pythonic_params = pythonic_params
        self.uri_parser_class = uri_parser_class
        self.jsonifier = jsonifier

        self.arguments, self.has_kwargs = None, None

    @property
    @abc.abstractmethod
    def _parameter_decorator_cls(self) -> t.Type[BaseParameterDecorator]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _response_decorator_cls(self) -> t.Type[BaseResponseDecorator]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _sync_async_decorator(self) -> t.Callable[[t.Callable], t.Callable]:
        """Decorator to translate between sync and async functions."""
        raise NotImplementedError

    @property
    def uri_parser(self):
        uri_parser_class = self.uri_parser_class or operation.uri_parser_class
        return uri_parser_class(operation.parameters, operation.body_definition())

    def decorate(self, function: t.Callable) -> t.Callable:
        """Decorate a function with decorators based on the operation."""
        function = self._sync_async_decorator(function)

        parameter_decorator = self._parameter_decorator_cls(
            framework=self.framework,
            pythonic_params=self.pythonic_params,
        )
        function = parameter_decorator(function)

        response_decorator = self._response_decorator_cls(
            framework=self.framework,
            jsonifier=self.jsonifier,
        )
        function = response_decorator(function)

        return function

    @abc.abstractmethod
    def __call__(self, function: t.Callable) -> t.Callable:
        raise NotImplementedError


class WSGIDecorator(BaseDecorator):
    """Decorator for usage with WSGI apps. The parameter decorator works with a Flask request,
    and provides Flask datastructures to the view function. This works for any WSGI app, since
    we get the request via the connexion context provided by WSGI middleware.

    This decorator does not parse responses, but passes them directly to the WSGI App."""

    framework = FlaskFramework

    @property
    def _parameter_decorator_cls(self) -> t.Type[SyncParameterDecorator]:
        return SyncParameterDecorator

    @property
    def _response_decorator_cls(self) -> t.Type[BaseResponseDecorator]:
        return NoResponseDecorator

    @property
    def _sync_async_decorator(self) -> t.Callable[[t.Callable], t.Callable]:
        def decorator(function: t.Callable) -> t.Callable:
            @functools.wraps(function)
            def wrapper(*args, **kwargs) -> t.Callable:
                if asyncio.iscoroutinefunction(function):
                    return async_to_sync(function)(*args, **kwargs)
                else:
                    return function(*args, **kwargs)

            return wrapper

        return decorator

    def __call__(self, function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            request = self.framework.get_request(uri_parser=self.uri_parser)
            decorated_function = self.decorate(function)
            return decorated_function(request)

        return wrapper


class FlaskDecorator(WSGIDecorator):
    """Decorator for usage with Connexion or Flask apps. The parameter decorator works with a
    Flask request, and provides Flask datastructures to the view function.

    The response decorator returns Flask responses."""

    @property
    def _response_decorator_cls(self) -> t.Type[SyncResponseDecorator]:
        return SyncResponseDecorator


class ASGIDecorator(BaseDecorator):
    """Decorator for usage with ASGI apps. The parameter decorator works with a Starlette request,
    and provides Starlette datastructures to the view function. This works for any ASGI app, since
    we get the request via the connexion context provided by ASGI middleware.

    This decorator does not parse responses, but passes them directly to the ASGI App."""

    framework = StarletteFramework

    @property
    def _parameter_decorator_cls(self) -> t.Type[AsyncParameterDecorator]:
        return AsyncParameterDecorator

    @property
    def _response_decorator_cls(self) -> t.Type[BaseResponseDecorator]:
        return NoResponseDecorator

    @property
    def _sync_async_decorator(self) -> t.Callable[[t.Callable], t.Callable]:
        def decorator(function: t.Callable) -> t.Callable:
            @functools.wraps(function)
            async def wrapper(*args, **kwargs):
                if asyncio.iscoroutinefunction(function):
                    return await function(*args, **kwargs)
                else:
                    return await run_in_threadpool(function, *args, **kwargs)

            return wrapper

        return decorator

    def __call__(self, function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            request = self.framework.get_request(
                uri_parser=self.uri_parser, scope=scope, receive=receive
            )
            decorated_function = self.decorate(function)
            return await decorated_function(request)

        return wrapper


class StarletteDecorator(ASGIDecorator):
    """Decorator for usage with Connexion or Starlette apps. The parameter decorator works with a
    Starlette request, and provides Starlette datastructures to the view function.

    The response decorator returns Starlette responses."""

    @property
    def _response_decorator_cls(self) -> t.Type[AsyncResponseDecorator]:
        return AsyncResponseDecorator
