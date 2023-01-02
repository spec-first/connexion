import abc
import asyncio
import functools
import typing as t

from asgiref.sync import async_to_sync
from starlette.concurrency import run_in_threadpool

from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    SyncParameterDecorator,
    inspect_function_arguments,
)
from connexion.operations import AbstractOperation
from connexion.uri_parsing import AbstractURIParser


class BaseDecorator:
    def __init__(
        self,
        operation_spec: AbstractOperation,
        *,
        uri_parser_cls: t.Type[AbstractURIParser],
        framework,
        parameter: bool,
        response: bool,
        pythonic_params: bool = False,
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

        self.arguments, self.has_kwargs = None, None
        if self.parameter:
            self.arguments, self.has_kwargs = inspect_function_arguments(
                operation_spec.function
            )

    @property
    @abc.abstractmethod
    def _parameter_decorator_cls(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _response_decorator_cls(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _sync_async_decorator(self) -> t.Callable:
        raise NotImplementedError

    def decorate(self, function: t.Callable) -> t.Callable:
        function = self._sync_async_decorator(function)

        # if self.response:
        #     response_decorator = self._response_decorator_cls()
        #     function = response_decorator(function)

        if self.parameter:
            parameter_decorator = self._parameter_decorator_cls(
                self.operation_spec,
                get_body_fn=self.framework.get_body,
                arguments=self.arguments,
                has_kwargs=self.has_kwargs,
                pythonic_params=self.pythonic_params,
            )
            function = parameter_decorator(function)

        return function

    @abc.abstractmethod
    def __call__(self, function: t.Callable) -> t.Callable:
        raise NotImplementedError


class SyncDecorator(BaseDecorator):
    @property
    def _parameter_decorator_cls(self):
        return SyncParameterDecorator

    @property
    def _response_decorator_cls(self):
        pass

    @property
    def _sync_async_decorator(self) -> t.Callable:
        def wrapper(function: t.Callable) -> t.Callable:
            if asyncio.iscoroutinefunction(function):
                return async_to_sync(function)
            else:
                return function

        return wrapper

    def __call__(self, function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            connexion_request = self.framework.get_request(
                *args, uri_parser=self.uri_parser, **kwargs
            )

            decorated_function = self.decorate(function)
            connexion_response = decorated_function(connexion_request)

            # TODO: take response into account
            mime_type = self.operation_spec.get_mimetype()

            framework_response = self.framework.get_response(
                connexion_response, mime_type
            )
            return framework_response

        return wrapper


class AsyncDecorator(BaseDecorator):
    @property
    def _parameter_decorator_cls(self):
        return AsyncParameterDecorator

    @property
    def _response_decorator_cls(self):
        pass

    @property
    def _sync_async_decorator(self) -> t.Callable:
        async def wrapper(function: t.Callable) -> t.Callable:
            if asyncio.iscoroutinefunction(function):
                return function
            else:
                return functools.partial(run_in_threadpool, function)

        return wrapper

    def __call__(self, function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            connexion_request = await self.framework.get_request(
                *args, uri_parser=self.uri_parser, **kwargs
            )

            decorated_function = self.decorate(function)

            connexion_response = await decorated_function(connexion_request)

            content_type = connexion_response.content_type
            if content_type is None:
                if len(self.produces) == 1:
                    content_type = self.produces[0]

            framework_response = await self.framework.get_response(
                connexion_response, content_type
            )

            return framework_response

        return wrapper
