import json

import requests

import pytest
from connexion.decorators.security import (get_tokeninfo_func,
                                           get_tokeninfo_remote,
                                           validate_scope, verify_apikey,
                                           verify_basic, verify_oauth)
from connexion.exceptions import (OAuthProblem, OAuthResponseProblem,
                                  OAuthScopeProblem)
from mock import MagicMock


def test_get_tokeninfo_url(monkeypatch):
    env = {}
    monkeypatch.setattr('os.environ', env)
    logger = MagicMock()
    monkeypatch.setattr('connexion.decorators.security.logger', logger)
    security_def = {}
    assert get_tokeninfo_func(security_def) is None
    logger.warn.assert_not_called()
    env['TOKENINFO_URL'] = 'issue-146'
    func = get_tokeninfo_func(security_def)
    assert func.func is get_tokeninfo_remote
    assert func.args == ('issue-146',)
    logger.warn.assert_not_called()
    logger.warn.reset_mock()
    security_def = {'x-tokenInfoUrl': 'bar'}
    func = get_tokeninfo_func(security_def)
    assert func.func is get_tokeninfo_remote
    assert func.args == ('bar',)
    logger.warn.assert_not_called()


def test_verify_oauth_missing_auth_header():
    def somefunc(token):
        return None

    wrapped_func = verify_oauth(somefunc, validate_scope)

    request = MagicMock()
    request.headers = {}

    assert wrapped_func(request, ['admin']) is None


def test_verify_oauth_scopes_remote(monkeypatch):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def get_tokeninfo_response(*args, **kwargs):
        tokeninfo_response = requests.Response()
        tokeninfo_response.status_code = requests.codes.ok
        tokeninfo_response._content = json.dumps(tokeninfo).encode()
        return tokeninfo_response

    token_info_func = get_tokeninfo_func({'x-tokenInfoUrl': 'https://example.org/tokeninfo'})
    wrapped_func = verify_oauth(token_info_func, validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    session = MagicMock()
    session.get = get_tokeninfo_response
    monkeypatch.setattr('connexion.decorators.security.session', session)

    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"] += " admin"
    assert wrapped_func(request, ['admin']) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"].append("admin")
    assert wrapped_func(request, ['admin']) is not None


def test_verify_oauth_invalid_local_token_response_none():
    def somefunc(token):
        return None

    wrapped_func = verify_oauth(somefunc, validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthResponseProblem):
        wrapped_func(request, ['admin'])


def test_verify_oauth_scopes_local():
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def token_info(token):
        return tokeninfo

    wrapped_func = verify_oauth(token_info, validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"] += " admin"
    assert wrapped_func(request, ['admin']) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, message="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"].append("admin")
    assert wrapped_func(request, ['admin']) is not None


def test_verify_basic_missing_auth_header():
    def somefunc(username, password, required_scopes=None):
        return None

    wrapped_func = verify_basic(somefunc)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    assert wrapped_func(request, ['admin']) is None


def test_verify_basic():
    def basic_info(username, password, required_scopes=None):
        if username == 'foo' and password == 'bar':
            return {'sub': 'foo'}
        return None

    wrapped_func = verify_basic(basic_info)

    request = MagicMock()
    request.headers = {"Authorization": 'Basic Zm9vOmJhcg=='}

    assert wrapped_func(request, ['admin']) is not None


def test_verify_apikey_query():
    def apikey_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None

    wrapped_func = verify_apikey(apikey_info, 'query', 'auth')

    request = MagicMock()
    request.query = {"auth": 'foobar'}

    assert wrapped_func(request, ['admin']) is not None


def test_verify_apikey_header():
    def apikey_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None

    wrapped_func = verify_apikey(apikey_info, 'header', 'X-Auth')

    request = MagicMock()
    request.headers = {"X-Auth": 'foobar'}

    assert wrapped_func(request, ['admin']) is not None
