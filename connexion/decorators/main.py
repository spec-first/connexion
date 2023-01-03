import abc
import asyncio
import functools
import typing as t

from asgiref.sync import async_to_sync
from starlette.concurrency import run_in_threadpool

from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    BaseParameterDecorator,
    SyncParameterDecorator,
    inspect_function_arguments,
)
from connexion.decorators.response import (
    AsyncResponseDecorator,
    BaseResponseDecorator,
    SyncResponseDecorator,
)
from connexion.frameworks.abstract import Framework
from connexion.operations import AbstractOperation
from connexion.uri_parsing import AbstractURIParser


class BaseDecorator:
    """Base class for connexion decorators."""

    def __init__(
        self,
        operation_spec: AbstractOperation,
        *,
        uri_parser_cls: t.Type[AbstractURIParser],
        framework: t.Type[Framework],
        parameter: bool,
        response: bool,
        pythonic_params: bool = False,
        jsonifier,
    ) -> None:
        self.operation_spec = operation_spec
        self.uri_parser = uri_parser_cls(
            operation_spec.parameters, operation_spec.body_definition()
        )
        self.framework = framework
        self.produces = self.operation_spec.produces
        self.parameter = parameter
        self.response = response
        self.pythonic_params = pythonic_params
        self.jsonifier = jsonifier

        if self.parameter:
            self.arguments, self.has_kwargs = inspect_function_arguments(
                operation_spec.function
            )

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

        if self.parameter:
            parameter_decorator = self._parameter_decorator_cls(
                self.operation_spec,
                get_body_fn=self.framework.get_body,
                arguments=self.arguments,
                has_kwargs=self.has_kwargs,
                pythonic_params=self.pythonic_params,
            )
            function = parameter_decorator(function)

        if self.response:
            response_decorator = self._response_decorator_cls(
                self.operation_spec,
                framework=self.framework,
                jsonifier=self.jsonifier,
            )
            function = response_decorator(function)

        return function

    @abc.abstractmethod
    def __call__(self, function: t.Callable) -> t.Callable:
        raise NotImplementedError


class SyncDecorator(BaseDecorator):
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
            # TODO: move into parameter decorator?
            connexion_request = self.framework.get_request(
                *args, uri_parser=self.uri_parser, **kwargs
            )

            decorated_function = self.decorate(function)
            return decorated_function(connexion_request)

        return wrapper


class AsyncDecorator(BaseDecorator):
    @property
    def _parameter_decorator_cls(self) -> t.Type[AsyncParameterDecorator]:
        return AsyncParameterDecorator

    @property
    def _response_decorator_cls(self) -> t.Type[AsyncResponseDecorator]:
        return AsyncResponseDecorator

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
            # TODO: move into parameter decorator?
            connexion_request = self.framework.get_request(
                *args, uri_parser=self.uri_parser, **kwargs
            )

            decorated_function = self.decorate(function)
            response = decorated_function(connexion_request)
            while asyncio.iscoroutine(response):
                response = await response
            return response

        return wrapper
