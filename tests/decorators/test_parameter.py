from unittest.mock import MagicMock

from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    SyncParameterDecorator,
    pythonic,
)
from connexion.testing import TestContext


def test_sync_injection():
    request = MagicMock(name="request")
    request.path_params = {"p1": "123"}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    with TestContext(operation=operation):
        parameter_decorator = SyncParameterDecorator()
        decorated_handler = parameter_decorator(handler)
        decorated_handler(request)
    func.assert_called_with(p1="123")


async def test_async_injection():
    request = MagicMock(name="request")
    request.path_params = {"p1": "123"}

    func = MagicMock()

    async def handler(**kwargs):
        func(**kwargs)

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    with TestContext(operation=operation):
        parameter_decorator = AsyncParameterDecorator()
        decorated_handler = parameter_decorator(handler)
        await decorated_handler(request)
    func.assert_called_with(p1="123")


def test_sync_injection_with_context():
    request = MagicMock(name="request")
    request.path_params = {"p1": "123"}

    func = MagicMock()

    def handler(context_, **kwargs):
        func(context_, **kwargs)

    context = {"test": "success"}

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    with TestContext(context=context, operation=operation):
        parameter_decorator = SyncParameterDecorator()
        decorated_handler = parameter_decorator(handler)
        decorated_handler(request)
        func.assert_called_with(context, p1="123", test="success")


async def test_async_injection_with_context():
    request = MagicMock(name="request")
    request.path_params = {"p1": "123"}

    func = MagicMock()

    async def handler(context_, **kwargs):
        func(context_, **kwargs)

    context = {"test": "success"}

    operation = MagicMock(name="operation")
    operation.body_name = lambda _: "body"

    with TestContext(context=context, operation=operation):
        parameter_decorator = AsyncParameterDecorator()
        decorated_handler = parameter_decorator(handler)
        await decorated_handler(request)
        func.assert_called_with(context, p1="123", test="success")


def test_pythonic_params():
    assert pythonic("orderBy[eq]") == "order_by_eq"
    assert pythonic("ids[]") == "ids"
