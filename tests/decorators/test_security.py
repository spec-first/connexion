import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from connexion.exceptions import (
    BadRequestProblem,
    ConnexionException,
    OAuthProblem,
    OAuthResponseProblem,
    OAuthScopeProblem,
)
from connexion.lifecycle import ConnexionRequest
from connexion.security import (
    NO_VALUE,
    ApiKeySecurityHandler,
    BasicSecurityHandler,
    OAuthSecurityHandler,
    SecurityHandlerFactory,
)


def test_get_tokeninfo_url(monkeypatch):
    security_handler = OAuthSecurityHandler()
    security_handler.get_token_info_remote = MagicMock(
        return_value="get_token_info_remote_result"
    )
    env = {}
    monkeypatch.setattr("os.environ", env)
    logger = MagicMock()
    monkeypatch.setattr("connexion.security.logger", logger)

    security_def = {}
    assert security_handler.get_tokeninfo_func(security_def) is None
    logger.warn.assert_not_called()

    env["TOKENINFO_URL"] = "issue-146"
    assert (
        security_handler.get_tokeninfo_func(security_def)
        == "get_token_info_remote_result"
    )
    security_handler.get_token_info_remote.assert_called_with("issue-146")
    logger.warn.assert_not_called()
    logger.warn.reset_mock()

    security_def = {"x-tokenInfoUrl": "bar"}
    assert (
        security_handler.get_tokeninfo_func(security_def)
        == "get_token_info_remote_result"
    )
    security_handler.get_token_info_remote.assert_called_with("bar")
    logger.warn.assert_not_called()


def test_verify_oauth_missing_auth_header():
    def somefunc(token):
        return None

    security_handler = OAuthSecurityHandler()
    wrapped_func = security_handler._get_verify_func(
        somefunc, security_handler.validate_scope, ["admin"]
    )

    request = ConnexionRequest(scope={"type": "http", "headers": []})

    assert wrapped_func(request) is NO_VALUE


async def test_verify_oauth_scopes_remote(monkeypatch):
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    async def get_tokeninfo_response(*args, **kwargs):
        tokeninfo_response = requests.Response()
        tokeninfo_response.status_code = requests.codes.ok
        tokeninfo_response._content = json.dumps(tokeninfo).encode()
        return tokeninfo_response

    security_handler = OAuthSecurityHandler()
    token_info_func = security_handler.get_tokeninfo_func(
        {"x-tokenInfoUrl": "https://example.org/tokeninfo"}
    )
    wrapped_func = security_handler._get_verify_func(
        token_info_func, security_handler.validate_scope, ["admin"]
    )

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"authorization", b"Bearer 123"]]}
    )

    client = MagicMock()
    client.get = get_tokeninfo_response
    monkeypatch.setattr(OAuthSecurityHandler, "client", client)

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

    security_handler = OAuthSecurityHandler()
    wrapped_func = security_handler._get_verify_func(
        somefunc, security_handler.validate_scope, ["admin"]
    )

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"authorization", b"Bearer 123"]]}
    )

    with pytest.raises(OAuthResponseProblem):
        await wrapped_func(request)


async def test_verify_oauth_scopes_local():
    tokeninfo = dict(uid="foo", scope="scope1 scope2")

    def token_info(token):
        return tokeninfo

    security_handler = OAuthSecurityHandler()
    wrapped_func = security_handler._get_verify_func(
        token_info, security_handler.validate_scope, ["admin"]
    )

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"authorization", b"Bearer 123"]]}
    )

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

    security_handler = BasicSecurityHandler()
    wrapped_func = security_handler._get_verify_func(somefunc)

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"authorization", b"Bearer 123"]]}
    )

    assert wrapped_func(request) is NO_VALUE


async def test_verify_basic():
    def basic_info(username, password, required_scopes=None):
        if username == "foo" and password == "bar":
            return {"sub": "foo"}
        return None

    security_handler = BasicSecurityHandler()
    wrapped_func = security_handler._get_verify_func(basic_info)

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"authorization", b"Basic Zm9vOmJhcg=="]]}
    )

    assert await wrapped_func(request) is not None


async def test_verify_apikey_query():
    def apikey_info(apikey, required_scopes=None):
        if apikey == "foobar":
            return {"sub": "foo"}
        return None

    security_handler_factory = ApiKeySecurityHandler()
    wrapped_func = security_handler_factory._get_verify_func(
        apikey_info, "query", "auth", None
    )

    request = ConnexionRequest(scope={"type": "http", "query_string": b"auth=foobar"})

    assert await wrapped_func(request) is not None


async def test_verify_apikey_header():
    def apikey_info(apikey, required_scopes=None):
        if apikey == "foobar":
            return {"sub": "foo"}
        return None

    security_handler_factory = ApiKeySecurityHandler()
    wrapped_func = security_handler_factory._get_verify_func(
        apikey_info, "header", "X-Auth", None
    )

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"x-auth", b"foobar"]]}
    )

    assert await wrapped_func(request) is not None


async def test_verify_apikey_scopes():
    def apikey_info(apikey, required_scopes=None):
        if apikey == "admin foobar" and required_scopes == ["admin"]:
            return {"sub": "foo"}
        return None

    security_handler_factory = ApiKeySecurityHandler()

    scheme_apikey = {
        "type": "apiKey",
        "name": "x-auth",
        "in": "header",
        "scopes": {"admin"},
    }

    with patch.object(
        security_handler_factory,
        f"{security_handler_factory._resolve_func.__name__}",
        return_value=apikey_info,
    ) as mock_resolve_func:
        wrapped_func = security_handler_factory.get_fn(scheme_apikey, ["admin"])
        mock_resolve_func.assert_called_once()

        request = ConnexionRequest(
            scope={"type": "http", "headers": [[b"x-auth", b"admin foobar"]]}
        )

        assert await wrapped_func(request) == {"sub": "foo"}


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
    apikey_security_handler_factory = ApiKeySecurityHandler()
    wrapped_func_key1 = apikey_security_handler_factory._get_verify_func(
        apikey1_info, "header", "X-Auth-1", []
    )
    wrapped_func_key2 = apikey_security_handler_factory._get_verify_func(
        apikey2_info, "header", "X-Auth-2", []
    )
    schemes = {
        "key1": wrapped_func_key1,
        "key2": wrapped_func_key2,
    }
    wrapped_func = security_handler_factory.verify_multiple_schemes(schemes)

    # Single key does not succeed
    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"x-auth-1", b"foobar"]]}
    )

    assert await wrapped_func(request) is NO_VALUE

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"x-auth-2", b"bar"]]}
    )

    assert await wrapped_func(request) is NO_VALUE

    # Supplying both keys does succeed
    request = ConnexionRequest(
        scope={
            "type": "http",
            "headers": [[b"x-auth-1", b"foobar"], [b"x-auth-2", b"bar"]],
        }
    )

    expected_token_info = {
        "key1": {"sub": "foo"},
        "key2": {"sub": "bar"},
    }
    assert await wrapped_func(request) == expected_token_info


async def test_verify_security_oauthproblem():
    """Tests whether verify_security raises an OAuthProblem if there are no auth_funcs."""
    security_handler_factory = SecurityHandlerFactory()
    security_func = security_handler_factory.verify_security([])

    request = MagicMock(spec_set=ConnexionRequest)
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


async def test_optional_kwargs_injected():
    """Test that optional keyword arguments 'required_scopes' and 'request' are injected when
    defined as arguments in the user security function. This test uses the ApiKeySecurityHandler,
    but the tested behavior is generic across handlers."""
    security_handler_factory = ApiKeySecurityHandler()

    request = ConnexionRequest(
        scope={"type": "http", "headers": [[b"x-auth", b"foobar"]]}
    )

    def apikey_info_no_kwargs(key):
        """Will fail if additional keywords are injected."""
        return {"sub": "no_kwargs"}

    wrapped_func_no_kwargs = security_handler_factory._get_verify_func(
        apikey_info_no_kwargs, "header", "X-Auth", None
    )
    assert await wrapped_func_no_kwargs(request) == {"sub": "no_kwargs"}

    def apikey_info_request(key, request):
        """Will fail if request is not injected."""
        return {"sub": "request"}

    wrapped_func_request = security_handler_factory._get_verify_func(
        apikey_info_request, "header", "X-Auth", None
    )
    assert await wrapped_func_request(request) == {"sub": "request"}

    def apikey_info_scopes(key, required_scopes):
        """Will fail if required_scopes is not injected."""
        return {"sub": "scopes"}

    wrapped_func_scopes = security_handler_factory._get_verify_func(
        apikey_info_scopes, "header", "X-Auth", None
    )
    assert await wrapped_func_scopes(request) == {"sub": "scopes"}

    def apikey_info_kwargs(key, **kwargs):
        """Will fail if request and required_scopes are not injected."""
        assert "request" in kwargs
        assert "required_scopes" in kwargs
        return {"sub": "kwargs"}

    wrapped_func_kwargs = security_handler_factory._get_verify_func(
        apikey_info_kwargs, "header", "X-Auth", None
    )
    assert await wrapped_func_kwargs(request) == {"sub": "kwargs"}
