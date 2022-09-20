from unittest.mock import MagicMock

from connexion.decorators.parameter import parameter_to_arg, pythonic


def test_injection():
    request = MagicMock(name="request", path_params={"p1": "123"})
    request.args = {}
    request.headers = {}
    request.params = {}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    class Op:
        consumes = ["application/json"]

        def get_arguments(self, *args, **kwargs):
            return {"p1": "123"}

    parameter_to_arg(Op(), handler)(request)
    func.assert_called_with(p1="123")


def test_injection_with_context():
    request = MagicMock(
        name="request", path_params={"p1": "123"}, params={"context_": {"user": "456"}}
    )
    request.args = {}
    request.headers = {}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    class Op2:
        consumes = ["application/json"]

        def get_arguments(self, *args, **kwargs):
            return {"p1": "123", "context_": {"user": "456"}}

    parameter_to_arg(Op2(), handler)(request)
    func.assert_called_with(p1="123", context_={"user": "456"})


def test_pythonic_params():
    assert pythonic("orderBy[eq]") == "order_by_eq"
    assert pythonic("ids[]") == "ids"
