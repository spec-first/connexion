import json

import requests

import pytest
from connexion.decorators.security import (get_tokeninfo_url,
                                           verify_oauth_local,
                                           verify_oauth_remote)
from connexion.exceptions import (OAuthProblem, OAuthResponseProblem,
                                  OAuthScopeProblem)
from mock import MagicMock


def test_get_tokeninfo_url(monkeypatch):
    env = {}
    monkeypatch.setattr('os.environ', env)
    logger = MagicMock()
    monkeypatch.setattr('connexion.decorators.security.logger', logger)
    security_def = {}
    assert get_tokeninfo_url(security_def) is None
    logger.warn.assert_not_called()
    env['TOKENINFO_URL'] = 'issue-146'
    assert get_tokeninfo_url(security_def) == 'issue-146'
    logger.warn.assert_not_called()
    logger.warn.reset_mock()
    security_def = {'x-tokenInfoUrl': 'bar'}
    assert get_tokeninfo_url(security_def) == 'bar'
    logger.warn.assert_not_called()


def test_verify_oauth_invalid_auth_header(monkeypatch):
    def func():
        pass

    wrapped_func = verify_oauth_remote('https://example.org/tokeninfo', set(['admin']), func)

    request = MagicMock()
    app = MagicMock()
    monkeypatch.setattr('flask.current_app', app)

    with pytest.raises(OAuthProblem):
        wrapped_func(request)


def test_verify_oauth_scopes_remote(monkeypatch):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def get_tokeninfo_response(*args, **kwargs):
        tokeninfo_response = requests.Response()
        tokeninfo_response.status_code = requests.codes.ok
        tokeninfo_response._content = json.dumps(tokeninfo).encode()
        return tokeninfo_response

    def func(request):
        pass

    wrapped_func = verify_oauth_remote('https://example.org/tokeninfo', set(['admin']), func)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}
    app = MagicMock()
    monkeypatch.setattr('flask.current_app', app)

    session = MagicMock()
    session.get = get_tokeninfo_response
    monkeypatch.setattr('connexion.decorators.security.session', session)

    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request)

    tokeninfo["scope"] += " admin"
    wrapped_func(request)

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request)

    tokeninfo["scope"].append("admin")
    wrapped_func(request)


def test_verify_oauth_invalid_local_token_response_none(monkeypatch):
    def somefunc(token):
        return None

    def func():
        pass

    wrapped_func = verify_oauth_local(somefunc, set(['admin']), func)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}
    app = MagicMock()
    monkeypatch.setattr('flask.current_app', app)

    with pytest.raises(OAuthResponseProblem):
        wrapped_func(request)


def test_verify_oauth_scopes_local(monkeypatch):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def func(request):
        pass

    def token_info(token):
        return tokeninfo

    wrapped_func = verify_oauth_local(token_info, set(['admin']), func)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}
    app = MagicMock()
    monkeypatch.setattr('flask.current_app', app)

    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request)

    tokeninfo["scope"] += " admin"
    wrapped_func(request)

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request)

    tokeninfo["scope"].append("admin")
    wrapped_func(request)
