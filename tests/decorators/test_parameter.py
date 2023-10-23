import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from connexion.decorators.parameter import (
    AsyncParameterDecorator,
    SyncParameterDecorator,
    pythonic,
)
from connexion.frameworks.flask import Flask as FlaskFramework
from connexion.frameworks.starlette import Starlette as StarletteFramework
from connexion.testing import TestContext


def test_sync_injection():
    request = MagicMock(name="request")
    request.path_params = {"p1": "123"}
    request.get_body.return_value = {}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    operation = MagicMock(name="operation")
    operation.is_request_body_defined = False
    operation.body_name = lambda _: "body"

    with TestContext(operation=operation):
        parameter_decorator = SyncParameterDecorator(framework=FlaskFramework)
        decorated_handler = parameter_decorator(handler)
        decorated_handler(request)
    func.assert_called_with(p1="123")


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="AsyncMock only available from 3.8."
)
async def test_async_injection():
    request = AsyncMock(name="request")
    request.path_params = {"p1": "123"}
    request.get_body.return_value = {}
    request.files.return_value = {}

    func = MagicMock()

    async def handler(**kwargs):
        func(**kwargs)

    operation = MagicMock(name="operation")
    operation.is_request_body_defined = False
    operation.body_name = lambda _: "body"

    with TestContext(operation=operation):
        parameter_decorator = AsyncParameterDecorator(framework=StarletteFramework)
        decorated_handler = parameter_decorator(handler)
        await decorated_handler(request)
    func.assert_called_with(p1="123")


def test_sync_injection_with_context():
    request = MagicMock(name="request")
    request.path_params = {"p1": "123"}
    request.get_body.return_value = {}

    func = MagicMock()

    def handler(context_, **kwargs):
        func(context_, **kwargs)

    context = {"test": "success"}

    operation = MagicMock(name="operation")
    operation.is_request_body_defined = False
    operation.body_name = lambda _: "body"

    with TestContext(context=context, operation=operation):
        parameter_decorator = SyncParameterDecorator(framework=FlaskFramework)
        decorated_handler = parameter_decorator(handler)
        decorated_handler(request)
        func.assert_called_with(context, p1="123", test="success")


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="AsyncMock only available from 3.8."
)
async def test_async_injection_with_context():
    request = AsyncMock(name="request")
    request.path_params = {"p1": "123"}
    request.get_body.return_value = {}
    request.files.return_value = {}

    func = MagicMock()

    async def handler(context_, **kwargs):
        func(context_, **kwargs)

    context = {"test": "success"}

    operation = MagicMock(name="operation")
    operation.is_request_body_defined = False
    operation.body_name = lambda _: "body"

    with TestContext(context=context, operation=operation):
        parameter_decorator = AsyncParameterDecorator(framework=StarletteFramework)
        decorated_handler = parameter_decorator(handler)
        await decorated_handler(request)
        func.assert_called_with(context, p1="123", test="success")


def test_pythonic_params():
    assert pythonic("orderBy[eq]") == "order_by_eq"
    assert pythonic("ids[]") == "ids"
