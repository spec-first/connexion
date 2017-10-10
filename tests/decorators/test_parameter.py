from connexion.decorators.parameter import parameter_to_arg
# we are using "mock" module here for Py 2.7 support
from mock import MagicMock


def test_injection(monkeypatch):
    request = MagicMock(name='request', path_params={'p1': '123'})
    request.args = {}
    request.headers = {}
    request.params = {}

    func = MagicMock()
    parameter_to_arg({}, [], func)(request)

    func.assert_called_with(p1='123')
