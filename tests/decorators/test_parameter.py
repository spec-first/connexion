from unittest.mock import MagicMock

from connexion.decorators.parameter import parameter_to_arg, pythonic


async def test_injection():
    request = MagicMock(name="request")
    request.query_params = {}
    request.path_params = {"p1": "123"}
    request.headers = {}
    request.content_type = "application/json"

    async def coro():
        return

    request.json = coro
    request.loop = None
    request.context = {}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    class Op:
        consumes = ["application/json"]
        parameters = []
        method = "GET"

        def body_name(self, *args, **kwargs):
            return "body"

    parameter_decorator = parameter_to_arg(Op(), handler)
    parameter_decorator(request)
    func.assert_called_with(p1="123")


async def test_injection_with_context():
    request = MagicMock(name="request")

    async def coro():
        return

    request.json = coro
    request.loop = None
    request.context = {}
    request.content_type = "application/json"
    request.path_params = {"p1": "123"}

    func = MagicMock()

    def handler(context_, **kwargs):
        func(context_, **kwargs)

    class Op2:
        consumes = ["application/json"]
        parameters = []
        method = "GET"

        def body_name(self, *args, **kwargs):
            return "body"

    parameter_decorator = parameter_to_arg(Op2(), handler)
    parameter_decorator(request)
    func.assert_called_with(request.context, p1="123")


def test_pythonic_params():
    assert pythonic("orderBy[eq]") == "order_by_eq"
    assert pythonic("ids[]") == "ids"
