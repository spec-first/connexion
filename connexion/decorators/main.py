import abc
import asyncio
import functools
import json
import typing as t

from asgiref.sync import async_to_sync
from starlette.concurrency import run_in_threadpool

from connexion.context import operation
from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    BaseParameterDecorator,
    SyncParameterDecorator,
)
from connexion.decorators.response import (
    AsyncResponseDecorator,
    BaseResponseDecorator,
    SyncResponseDecorator,
)
from connexion.frameworks.abstract import Framework
from connexion.frameworks.flask import Flask as FlaskFramework
from connexion.frameworks.starlette import Starlette as StarletteFramework


class BaseDecorator:
    """Base class for connexion decorators."""

    framework: t.Type[Framework]

    def __init__(
        self,
        *,
        pythonic_params: bool = False,
        jsonifier=json,
    ) -> None:
        self.pythonic_params = pythonic_params
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

    def decorate(self, function: t.Callable) -> t.Callable:
        """Decorate a function with decorators based on the operation."""
        function = self._sync_async_decorator(function)

        parameter_decorator = self._parameter_decorator_cls(
            operation,
            get_body_fn=self.framework.get_body,
            pythonic_params=self.pythonic_params,
        )
        function = parameter_decorator(function)

        response_decorator = self._response_decorator_cls(
            operation,
            framework=self.framework,
            jsonifier=self.jsonifier,
        )
        function = response_decorator(function)

        return function

    @abc.abstractmethod
    def __call__(self, function: t.Callable) -> t.Callable:
        raise NotImplementedError


class FlaskDecorator(BaseDecorator):
    """Decorator for usage with Flask. The parameter decorator works with a Flask request,
    and provides Flask datastructures to the view function. The response decorator returns
    a Flask response"""

    framework = FlaskFramework

    @property
    def _parameter_decorator_cls(self) -> t.Type[SyncParameterDecorator]:
        return SyncParameterDecorator

    @property
    def _response_decorator_cls(self) -> t.Type[SyncResponseDecorator]:
        return SyncResponseDecorator

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
            decorated_function = self.decorate(function)
            return decorated_function()

        return wrapper


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
        class NoResponseDecorator(BaseResponseDecorator):
            def __call__(self, function: t.Callable) -> t.Callable:
                return lambda request: function(request)

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
            decorated_function = self.decorate(function)
            response = decorated_function()
            while asyncio.iscoroutine(response):
                response = await response
            return response

        return wrapper


class StarletteDecorator(ASGIDecorator):
    """Decorator for usage with Connexion or Starlette apps. The parameter decorator works with a
    Starlette request, and provides Starlette datastructures to the view function.

    The response decorator returns Starlette responses."""

    @property
    def _response_decorator_cls(self) -> t.Type[AsyncResponseDecorator]:
        return AsyncResponseDecorator
