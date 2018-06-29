
from connexion.decorators.parameter import parameter_to_arg
# we are using "mock" module here for Py 2.7 support
from mock import MagicMock
from testfixtures import LogCapture


def test_injection(monkeypatch):
    request = MagicMock(name='request', path_params={'p1': '123'})
    request.args = {}
    request.headers = {}
    request.params = {}

    func = MagicMock()

    def handler(**kwargs):
        func(**kwargs)

    class Op(object):
        consumes = ['application/json']

        def get_arguments(self, *args, **kwargs):
            return {"p1": "123"}

    parameter_to_arg(Op(), handler)(request)

    func.assert_called_with(p1='123')


def test_query_sanitazion(query_sanitazion):
    app_client = query_sanitazion.app.test_client()
    #l = LogCapture()

    url = '/v1.0/greeting'
    response = app_client.post(url, data={'name': 'Jane Doe'})
    # This is ugly. The reason for asserting the logging in this way
    # is that in order to use LogCapture().check, we'd have to assert that
    # a specific sequence of logging has occurred. This is too restricting
    # for future development, and we are really only interested in the fact
    # a single message is logged.
    #messages = [x.strip() for x in str(l).split("\n")]
    #assert "FormData parameter 'name' in function arguments" in messages
    #assert "Query Parameter 'name' in function arguments" not in messages
    assert response.status_code == 200
    #l.uninstall()
