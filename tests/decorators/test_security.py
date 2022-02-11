import json
from unittest.mock import MagicMock

import pytest
import requests
from connexion.exceptions import (OAuthProblem, OAuthResponseProblem,
                                  OAuthScopeProblem)


def test_get_tokeninfo_url(monkeypatch, security_handler_factory):
    security_handler_factory.get_token_info_remote = MagicMock(return_value='get_token_info_remote_result')
    env = {}
    monkeypatch.setattr('os.environ', env)
    logger = MagicMock()
    monkeypatch.setattr('connexion.security.security_handler_factory.logger', logger)

    security_def = {}
    assert security_handler_factory.get_tokeninfo_func(security_def) is None
    logger.warn.assert_not_called()

    env['TOKENINFO_URL'] = 'issue-146'
    assert security_handler_factory.get_tokeninfo_func(security_def) == 'get_token_info_remote_result'
    security_handler_factory.get_token_info_remote.assert_called_with('issue-146')
    logger.warn.assert_not_called()
    logger.warn.reset_mock()

    security_def = {'x-tokenInfoUrl': 'bar'}
    assert security_handler_factory.get_tokeninfo_func(security_def) == 'get_token_info_remote_result'
    security_handler_factory.get_token_info_remote.assert_called_with('bar')
    logger.warn.assert_not_called()


def test_verify_oauth_missing_auth_header(security_handler_factory):
    def somefunc(token):
        return None

    wrapped_func = security_handler_factory.verify_oauth(somefunc, security_handler_factory.validate_scope)

    request = MagicMock()
    request.headers = {}

    assert wrapped_func(request, ['admin']) is security_handler_factory.no_value


def test_verify_oauth_scopes_remote(monkeypatch, security_handler_factory):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def get_tokeninfo_response(*args, **kwargs):
        tokeninfo_response = requests.Response()
        tokeninfo_response.status_code = requests.codes.ok
        tokeninfo_response._content = json.dumps(tokeninfo).encode()
        return tokeninfo_response

    token_info_func = security_handler_factory.get_tokeninfo_func({'x-tokenInfoUrl': 'https://example.org/tokeninfo'})
    wrapped_func = security_handler_factory.verify_oauth(token_info_func, security_handler_factory.validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    session = MagicMock()
    session.get = get_tokeninfo_response
    monkeypatch.setattr('connexion.security.flask_security_handler_factory.session', session)

    with pytest.raises(OAuthScopeProblem, match="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"] += " admin"
    assert wrapped_func(request, ['admin']) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem, match="Provided token doesn't have the required scope"):
        wrapped_func(request, ['admin'])

    tokeninfo["scope"].append("admin")
    assert wrapped_func(request, ['admin']) is not None


def test_verify_oauth_invalid_local_token_response_none(security_handler_factory):
    def somefunc(token):
        return None

    wrapped_func = security_handler_factory.verify_oauth(somefunc, security_handler_factory.validate_scope)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthResponseProblem):
        wrapped_func(request, ['admin'])


def test_verify_oauth_scopes_local(security_handler_factory):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def token_info(token):
        return tokeninfo

    wrapped_func = security_handler_factory.verify_oauth(token_info, security_handler_factory.validate_scope)

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


def test_verify_basic_missing_auth_header(security_handler_factory):
    def somefunc(username, password, required_scopes=None):
        return None

    wrapped_func = security_handler_factory.verify_basic(somefunc)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    assert wrapped_func(request, ['admin']) is security_handler_factory.no_value


def test_verify_basic(security_handler_factory):
    def basic_info(username, password, required_scopes=None):
        if username == 'foo' and password == 'bar':
            return {'sub': 'foo'}
        return None

    wrapped_func = security_handler_factory.verify_basic(basic_info)

    request = MagicMock()
    request.headers = {"Authorization": 'Basic Zm9vOmJhcg=='}

    assert wrapped_func(request, ['admin']) is not None


def test_verify_apikey_query(security_handler_factory):
    def apikey_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None

    wrapped_func = security_handler_factory.verify_api_key(apikey_info, 'query', 'auth')

    request = MagicMock()
    request.query = {"auth": 'foobar'}

    assert wrapped_func(request, ['admin']) is not None


def test_verify_apikey_header(security_handler_factory):
    def apikey_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None

    wrapped_func = security_handler_factory.verify_api_key(apikey_info, 'header', 'X-Auth')

    request = MagicMock()
    request.headers = {"X-Auth": 'foobar'}

    assert wrapped_func(request, ['admin']) is not None


def test_multiple_schemes(security_handler_factory):
    def apikey1_info(apikey, required_scopes=None):
        if apikey == 'foobar':
            return {'sub': 'foo'}
        return None
    def apikey2_info(apikey, required_scopes=None):
        if apikey == 'bar':
            return {'sub': 'bar'}
        return None

    wrapped_func_key1 = security_handler_factory.verify_api_key(apikey1_info, 'header', 'X-Auth-1')
    wrapped_func_key2 = security_handler_factory.verify_api_key(apikey2_info, 'header', 'X-Auth-2')
    schemes = {
        'key1': wrapped_func_key1,
        'key2': wrapped_func_key2,
    }
    wrapped_func = security_handler_factory.verify_multiple_schemes(schemes)

    # Single key does not succeed
    request = MagicMock()
    request.headers = {"X-Auth-1": 'foobar'}

    assert wrapped_func(request, ['admin']) is security_handler_factory.no_value

    request = MagicMock()
    request.headers = {"X-Auth-2": 'bar'}

    assert wrapped_func(request, ['admin']) is security_handler_factory.no_value

    # Supplying both keys does succeed
    request = MagicMock()
    request.headers = {
        "X-Auth-1": 'foobar',
        "X-Auth-2": 'bar'
    }

    expected_token_info = {
        'key1': {'sub': 'foo'},
        'key2': {'sub': 'bar'},
    }
    assert wrapped_func(request, ['admin']) == expected_token_info


def test_verify_security_oauthproblem(security_handler_factory):
    """Tests whether verify_security raises an OAuthProblem if there are no auth_funcs."""
    func_to_secure = MagicMock(return_value='func')
    secured_func = security_handler_factory.verify_security([], [], func_to_secure)

    request = MagicMock()
    with pytest.raises(OAuthProblem) as exc_info:
        secured_func(request)

    assert str(exc_info.value) == '401 Unauthorized: No authorization token provided'
