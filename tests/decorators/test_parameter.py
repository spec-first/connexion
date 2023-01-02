from unittest.mock import MagicMock

from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    SyncParameterDecorator,
    inspect_function_arguments,
    pythonic,
)


def test_sync_injection():
    request = MagicMock(name="request")
    request.query_params = {}
    request.path_params = {"p1": "123"}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    def get_body_fn(_request):
        return {}

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    arguments, has_kwargs = inspect_function_arguments(handler)

    parameter_decorator = SyncParameterDecorator(
        operation, get_body_fn=get_body_fn, arguments=arguments, has_kwargs=has_kwargs
    )
    decorated_handler = parameter_decorator(handler)
    decorated_handler(request)
    func.assert_called_with(p1="123")


async def test_async_injection():
    request = MagicMock(name="request")
    request.query_params = {}
    request.path_params = {"p1": "123"}

    func = MagicMock()

    async def handler(**kwargs):
        func(**kwargs)

    def get_body_fn(_request):
        return {}

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    arguments, has_kwargs = inspect_function_arguments(handler)

    parameter_decorator = AsyncParameterDecorator(
        operation, get_body_fn=get_body_fn, arguments=arguments, has_kwargs=has_kwargs
    )
    decorated_handler = parameter_decorator(handler)
    await decorated_handler(request)
    func.assert_called_with(p1="123")


def test_sync_injection_with_context():
    request = MagicMock(name="request")
    request.query_params = {}
    request.path_params = {"p1": "123"}
    request.context = {}

    func = MagicMock()

    def handler(context_, **kwargs):
        func(context_, **kwargs)

    def get_body_fn(_request):
        return {}

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    arguments, has_kwargs = inspect_function_arguments(handler)

    parameter_decorator = SyncParameterDecorator(
        operation, get_body_fn=get_body_fn, arguments=arguments, has_kwargs=has_kwargs
    )
    decorated_handler = parameter_decorator(handler)
    decorated_handler(request)
    func.assert_called_with(request.context, p1="123")


async def test_async_injection_with_context():
    request = MagicMock(name="request")
    request.query_params = {}
    request.path_params = {"p1": "123"}
    request.context = {}

    func = MagicMock()

    async def handler(context_, **kwargs):
        func(context_, **kwargs)

    def get_body_fn(_request):
        return {}

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    arguments, has_kwargs = inspect_function_arguments(handler)

    parameter_decorator = AsyncParameterDecorator(
        operation, get_body_fn=get_body_fn, arguments=arguments, has_kwargs=has_kwargs
    )
    decorated_handler = parameter_decorator(handler)
    await decorated_handler(request)
    func.assert_called_with(request.context, p1="123")


def test_pythonic_params():
    assert pythonic("orderBy[eq]") == "order_by_eq"
    assert pythonic("ids[]") == "ids"
