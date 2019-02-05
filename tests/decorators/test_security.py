import json

import pytest
import requests
from unittest.mock import MagicMock

from connexion.exceptions import (OAuthResponseProblem, OAuthScopeProblem)
from connexion.security import SecurityHandlerFactory


def test_get_tokeninfo_url(monkeypatch):
    env = {}
    monkeypatch.setattr('os.environ', env)
    logger = MagicMock()
    monkeypatch.setattr('connexion.security.security_handler_factory.logger', logger)
    security_def = {}
    assert SecurityHandlerFactory.get_tokeninfo_func(security_def) is None
    logger.warn.assert_not_called()
    env['TOKENINFO_URL'] = 'issue-146'
    func = SecurityHandlerFactory.get_tokeninfo_func(security_def)
    assert func.func is SecurityHandlerFactory.get_token_info_remote
    assert func.args == ('issue-146',)
    logger.warn.assert_not_called()
    logger.warn.reset_mock()
    security_def = {'x-tokenInfoUrl': 'bar'}
    func = SecurityHandlerFactory.get_tokeninfo_func(security_def)
    assert func.func is SecurityHandlerFactory.get_token_info_remote
    assert func.args == ('bar',)
    logger.warn.assert_not_called()


def test_verify_oauth_missing_auth_header():
    def somefunc(token):
        return None

    wrapped_func = SecurityHandlerFactory.verify_oauth(somefunc, SecurityHandlerFactory.validate_scope)

    request = MagicMock()
    request.headers = {}

    assert wrapped_func(request, ['admin']) is SecurityHandlerFactory.no_value


def test_verify_oauth_scopes_remote(monkeypatch):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def get_tokeninfo_response(*args, **kwargs):
        tokeninfo_response = requests.Response()
        tokeninfo_response.status_code = requests.codes.ok
        tokeninfo_response._content = json.dumps(tokeninfo).encode()
        return tokeninfo_response

    token_info_func = SecurityHandlerFactory.get_tokeninfo_func({'x-tokenInfoUrl': 'https://example.org/tokeninfo'})
    wrapped_func = SecurityHandlerFactory.verify_oauth(token_info_func, SecurityHandlerFactory.validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    session = MagicMock()
    session.get = get_tokeninfo_response
    monkeypatch.setattr('connexion.security.security_handler_factory.session', session)

    with pytest.raises(OAuthScopeProblem, match="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"] += " admin"
    assert wrapped_func(request, ['admin']) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, match="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"].append("admin")
    assert wrapped_func(request, ['admin']) is not None


def test_verify_oauth_invalid_local_token_response_none():
    def somefunc(token):
        return None

    wrapped_func = SecurityHandlerFactory.verify_oauth(somefunc, SecurityHandlerFactory.validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthResponseProblem):
        wrapped_func(request, ['admin'])


def test_verify_oauth_scopes_local():
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def token_info(token):
        return tokeninfo

    wrapped_func = SecurityHandlerFactory.verify_oauth(token_info, SecurityHandlerFactory.validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthScopeProblem, match="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"] += " admin"
    assert wrapped_func(request, ['admin']) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, match="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"].append("admin")
    assert wrapped_func(request, ['admin']) is not None


def test_verify_basic_missing_auth_header():
    def somefunc(username, password, required_scopes=None):
        return None

    wrapped_func = SecurityHandlerFactory.verify_basic(somefunc)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    assert wrapped_func(request, ['admin']) is SecurityHandlerFactory.no_value


def test_verify_basic():
    def basic_info(username, password, required_scopes=None):
        if username == 'foo' and password == 'bar':
            return {'sub': 'foo'}
        return None

    wrapped_func = SecurityHandlerFactory.verify_basic(basic_info)

    request = MagicMock()
    request.headers = {"Authorization": 'Basic Zm9vOmJhcg=='}

    assert wrapped_func(request, ['admin']) is not None


def test_verify_apikey_query():
    def apikey_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None

    wrapped_func = SecurityHandlerFactory.verify_api_key(apikey_info, 'query', 'auth')

    request = MagicMock()
    request.query = {"auth": 'foobar'}

    assert wrapped_func(request, ['admin']) is not None


def test_verify_apikey_header():
    def apikey_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None

    wrapped_func = SecurityHandlerFactory.verify_api_key(apikey_info, 'header', 'X-Auth')

    request = MagicMock()
    request.headers = {"X-Auth": 'foobar'}

    assert wrapped_func(request, ['admin']) is not None
