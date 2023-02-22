import json
from unittest.mock import MagicMock

import pytest
import requests
from connexion.exceptions import (
    BadRequestProblem,
    ConnexionException,
    OAuthProblem,
    OAuthResponseProblem,
    OAuthScopeProblem,
)
from connexion.security import SecurityHandlerFactory


def test_get_tokeninfo_url(monkeypatch):
    security_handler_factory = SecurityHandlerFactory()
    security_handler_factory.get_token_info_remote = MagicMock(
        return_value="get_token_info_remote_result"
    )
    env = {}
    monkeypatch.setattr("os.environ", env)
    logger = MagicMock()
    monkeypatch.setattr("connexion.security.logger", logger)

    security_def = {}
    assert security_handler_factory.get_tokeninfo_func(security_def) is None
    logger.warn.assert_not_called()

    env["TOKENINFO_URL"] = "issue-146"
    assert (
        security_handler_factory.get_tokeninfo_func(security_def)
        == "get_token_info_remote_result"
    )
    security_handler_factory.get_token_info_remote.assert_called_with("issue-146")
    logger.warn.assert_not_called()
    logger.warn.reset_mock()

    security_def = {"x-tokenInfoUrl": "bar"}
    assert (
        security_handler_factory.get_tokeninfo_func(security_def)
        == "get_token_info_remote_result"
    )
    security_handler_factory.get_token_info_remote.assert_called_with("bar")
    logger.warn.assert_not_called()


def test_verify_oauth_missing_auth_header():
    def somefunc(token):
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_oauth(
        somefunc, security_handler_factory.validate_scope, ["admin"]
    )

    request = MagicMock()
    request.headers = {}

    assert wrapped_func(request) is security_handler_factory.no_value


async def test_verify_oauth_scopes_remote(monkeypatch):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    async def get_tokeninfo_response(*args, **kwargs):
        tokeninfo_response = requests.Response()
        tokeninfo_response.status_code = requests.codes.ok
        tokeninfo_response._content = json.dumps(tokeninfo).encode()
        return tokeninfo_response

    security_handler_factory = SecurityHandlerFactory()
    token_info_func = security_handler_factory.get_tokeninfo_func(
        {"x-tokenInfoUrl": "https://example.org/tokeninfo"}
    )
    wrapped_func = security_handler_factory.verify_oauth(
        token_info_func, security_handler_factory.validate_scope, ["admin"]
    )

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    client = MagicMock()
    client.get = get_tokeninfo_response
    monkeypatch.setattr(SecurityHandlerFactory, "client", client)

    with pytest.raises(OAuthScopeProblem) as exc_info:
        await wrapped_func(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.startswith(
        "Provided token does not have the required scope"
    )

    tokeninfo["scope"] += " admin"
    assert await wrapped_func(request) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem) as exc_info:
        await wrapped_func(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.startswith(
        "Provided token does not have the required scope"
    )

    tokeninfo["scope"].append("admin")
    assert await wrapped_func(request) is not None


async def test_verify_oauth_invalid_local_token_response_none():
    def somefunc(token):
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_oauth(
        somefunc, security_handler_factory.validate_scope, ["admin"]
    )

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthResponseProblem):
        await wrapped_func(request)


async def test_verify_oauth_scopes_local():
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def token_info(token):
        return tokeninfo

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_oauth(
        token_info, security_handler_factory.validate_scope, ["admin"]
    )

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    with pytest.raises(OAuthScopeProblem) as exc_info:
        await wrapped_func(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.startswith(
        "Provided token does not have the required scope"
    )

    tokeninfo["scope"] += " admin"
    assert await wrapped_func(request) is not None

    tokeninfo["scope"] = ["foo", "bar"]
    with pytest.raises(OAuthScopeProblem) as exc_info:
        await wrapped_func(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.startswith(
        "Provided token does not have the required scope"
    )

    tokeninfo["scope"].append("admin")
    assert await wrapped_func(request) is not None


def test_verify_basic_missing_auth_header():
    def somefunc(username, password, required_scopes=None):
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_basic(somefunc)

    request = MagicMock()
    request.headers = {"Authorization": "Bearer 123"}

    assert wrapped_func(request) is security_handler_factory.no_value


async def test_verify_basic():
    def basic_info(username, password, required_scopes=None):
        if username == "foo" and password == "bar":
            return {"sub": "foo"}
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_basic(basic_info)

    request = MagicMock()
    request.headers = {"Authorization": "Basic Zm9vOmJhcg=="}

    assert await wrapped_func(request) is not None


async def test_verify_apikey_query():
    def apikey_info(apikey, required_scopes=None):
        if apikey == "foobar":
            return {"sub": "foo"}
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_api_key(apikey_info, "query", "auth")

    request = MagicMock()
    request.query = {"auth": "foobar"}

    assert await wrapped_func(request) is not None


async def test_verify_apikey_header():
    def apikey_info(apikey, required_scopes=None):
        if apikey == "foobar":
            return {"sub": "foo"}
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func = security_handler_factory.verify_api_key(
        apikey_info, "header", "X-Auth"
    )

    request = MagicMock()
    request.headers = {"X-Auth": "foobar"}

    assert await wrapped_func(request) is not None


async def test_multiple_schemes():
    def apikey1_info(apikey, required_scopes=None):
        if apikey == "foobar":
            return {"sub": "foo"}
        return None

    def apikey2_info(apikey, required_scopes=None):
        if apikey == "bar":
            return {"sub": "bar"}
        return None

    security_handler_factory = SecurityHandlerFactory()
    wrapped_func_key1 = security_handler_factory.verify_api_key(
        apikey1_info, "header", "X-Auth-1"
    )
    wrapped_func_key2 = security_handler_factory.verify_api_key(
        apikey2_info, "header", "X-Auth-2"
    )
    schemes = {
        "key1": wrapped_func_key1,
        "key2": wrapped_func_key2,
    }
    wrapped_func = security_handler_factory.verify_multiple_schemes(schemes)

    # Single key does not succeed
    request = MagicMock()
    request.headers = {"X-Auth-1": "foobar"}

    assert await wrapped_func(request) is security_handler_factory.no_value

    request = MagicMock()
    request.headers = {"X-Auth-2": "bar"}

    assert await wrapped_func(request) is security_handler_factory.no_value

    # Supplying both keys does succeed
    request = MagicMock()
    request.headers = {"X-Auth-1": "foobar", "X-Auth-2": "bar"}

    expected_token_info = {
        "key1": {"sub": "foo"},
        "key2": {"sub": "bar"},
    }
    assert await wrapped_func(request) == expected_token_info


async def test_verify_security_oauthproblem():
    """Tests whether verify_security raises an OAuthProblem if there are no auth_funcs."""
    security_handler_factory = SecurityHandlerFactory()
    security_func = security_handler_factory.verify_security([])

    request = MagicMock()
    with pytest.raises(OAuthProblem) as exc_info:
        await security_func(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authorization token provided"


@pytest.mark.parametrize(
    "errors, most_specific",
    [
        ([OAuthProblem()], OAuthProblem),
        ([OAuthProblem(), OAuthScopeProblem([], [])], OAuthScopeProblem),
        (
            [OAuthProblem(), OAuthScopeProblem([], []), BadRequestProblem],
            OAuthScopeProblem,
        ),
        (
            [
                OAuthProblem(),
                OAuthScopeProblem([], []),
                BadRequestProblem,
                ConnexionException,
            ],
            OAuthScopeProblem,
        ),
        ([BadRequestProblem(), ConnexionException()], BadRequestProblem),
        ([ConnexionException()], ConnexionException),
    ],
)
def test_raise_most_specific(errors, most_specific):
    """Tests whether most specific exception is raised from a list."""
    security_handler_factory = SecurityHandlerFactory()
    with pytest.raises(most_specific):
        security_handler_factory._raise_most_specific(errors)
