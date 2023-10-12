import base64
import json

import pytest
from connexion import App
from connexion.exceptions import OAuthProblem
from connexion.security import NO_VALUE, BasicSecurityHandler, OAuthSecurityHandler


class FakeResponse:
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: str
        """
        self.status_code = status_code
        self.text = text
        self.ok = status_code == 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def oauth_requests(monkeypatch):
    class FakeClient:
        @staticmethod
        async def get(url, params=None, headers=None, timeout=None):
            """
            :type url: str
            :type params: dict| None
            """
            headers = headers or {}
            if url == "https://oauth.example/token_info":
                token = headers.get("Authorization", "invalid").split()[-1]
                if token in ["100", "has_myscope"]:
                    return FakeResponse(
                        200, '{"uid": "test-user", "scope": ["myscope"]}'
                    )
                if token in ["200", "has_wrongscope"]:
                    return FakeResponse(
                        200, '{"uid": "test-user", "scope": ["wrongscope"]}'
                    )
                if token == "has_myscope_otherscope":
                    return FakeResponse(
                        200, '{"uid": "test-user", "scope": ["myscope", "otherscope"]}'
                    )
                if token in ["300", "is_not_invalid"]:
                    return FakeResponse(404, "")
                if token == "has_scopes_in_scopes_with_s":
                    return FakeResponse(
                        200, '{"uid": "test-user", "scopes": ["myscope", "otherscope"]}'
                    )
            return url

    monkeypatch.setattr(OAuthSecurityHandler, "client", FakeClient())


def test_security_over_nonexistent_endpoints(oauth_requests, secure_api_app):
    app_client = secure_api_app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_inexistent_endpoint = app_client.get(
        "/v1.0/does-not-exist-invalid-token", headers=headers
    )
    assert get_inexistent_endpoint.status_code == 401
    assert (
        get_inexistent_endpoint.headers.get("content-type")
        == "application/problem+json"
    )

    headers = {"Authorization": "Bearer 100"}
    get_inexistent_endpoint = app_client.get(
        "/v1.0/does-not-exist-valid-token", headers=headers
    )
    assert get_inexistent_endpoint.status_code == 404
    assert (
        get_inexistent_endpoint.headers.get("content-type")
        == "application/problem+json"
    )

    get_inexistent_endpoint = app_client.get("/v1.0/does-not-exist-no-token")
    assert get_inexistent_endpoint.status_code == 401

    headers = {"Authorization": "Bearer 100"}
    post_greeting = app_client.post("/v1.0/greeting/rcaricio", data={}, headers=headers)
    assert post_greeting.status_code == 200

    post_greeting = app_client.post("/v1.0/greeting/rcaricio", data={})
    assert post_greeting.status_code == 401


def test_security(oauth_requests, secure_endpoint_app):
    app_client = secure_endpoint_app.test_client()

    get_bye_no_auth = app_client.get("/v1.0/byesecure/jsantos")
    assert get_bye_no_auth.status_code == 401
    assert get_bye_no_auth.headers.get("content-type") == "application/problem+json"
    get_bye_no_auth_response = get_bye_no_auth.json()
    assert get_bye_no_auth_response["detail"] == "No authorization token provided"

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get("/v1.0/byesecure/jsantos", headers=headers)
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.text == "Goodbye jsantos (Secure: test-user)"

    headers = {"Authorization": "Bearer 200"}
    get_bye_wrong_scope = app_client.get("/v1.0/byesecure/jsantos", headers=headers)
    assert get_bye_wrong_scope.status_code == 403
    assert get_bye_wrong_scope.headers.get("content-type") == "application/problem+json"
    get_bye_wrong_scope_response = get_bye_wrong_scope.json()
    assert get_bye_wrong_scope_response["detail"].startswith(
        "Provided token does not have the required scope"
    )

    headers = {"Authorization": "Bearer 300"}
    get_bye_bad_token = app_client.get("/v1.0/byesecure/jsantos", headers=headers)
    assert get_bye_bad_token.status_code == 401
    assert get_bye_bad_token.headers.get("content-type") == "application/problem+json"
    get_bye_bad_token_response = get_bye_bad_token.json()
    assert get_bye_bad_token_response["detail"] == "Provided token is not valid"

    response = app_client.get("/v1.0/more-than-one-security-definition")
    assert response.status_code == 401

    # also tests case-insensitivity
    headers = {"X-AUTH": "mykey"}
    response = app_client.get(
        "/v1.0/more-than-one-security-definition", headers=headers
    )
    assert response.status_code == 200

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get(
        "/v1.0/byesecure-ignoring-context/hjacobs", headers=headers
    )
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.text == "Goodbye hjacobs (Secure!)"

    headers = {"Authorization": "Bearer 100"}
    get_bye_from_flask = app_client.get("/v1.0/byesecure-from-flask", headers=headers)
    assert get_bye_from_flask.text == "Goodbye test-user (Secure!)"

    headers = {"Authorization": "Bearer 100"}
    get_bye_from_connexion = app_client.get(
        "/v1.0/byesecure-from-connexion", headers=headers
    )
    assert get_bye_from_connexion.text == "Goodbye test-user (Secure!)"

    headers = {"Authorization": "Bearer 100"}
    get_bye_from_connexion = app_client.get(
        "/v1.0/byesecure-jwt/test-user", headers=headers
    )
    assert get_bye_from_connexion.text == "Goodbye test-user (Secure: 100)"

    # has optional auth
    response = app_client.get("/v1.0/optional-auth")
    assert response.status_code == 200
    assert response.text == '"Unauthenticated"\n'
    headers = {"X-AUTH": "mykey"}
    response = app_client.get("/v1.0/optional-auth", headers=headers)
    assert response.status_code == 200
    assert response.text == '"Authenticated"\n'
    headers = {"X-AUTH": "wrong-key"}
    response = app_client.get("/v1.0/optional-auth", headers=headers)
    assert response.text == '"Unauthenticated"\n'
    assert response.status_code == 200

    # security function throws exception
    response = app_client.get("/v1.0/auth-exception", headers={"X-Api-Key": "foo"})
    assert response.status_code == 401


def test_checking_that_client_token_has_all_necessary_scopes(
    oauth_requests, secure_endpoint_app
):
    app_client = secure_endpoint_app.test_client()

    # has only one of the required scopes
    headers = {"Authorization": "Bearer has_myscope"}
    response = app_client.get("/v1.0/more-than-one-scope", headers=headers)
    assert response.status_code == 403

    # has none of the necessary scopes
    headers = {"Authorization": "Bearer has_wrongscope"}
    response = app_client.get("/v1.0/more-than-one-scope", headers=headers)
    assert response.status_code == 403

    # is not auth
    headers = {"Authorization": "Bearer is_not_invalid"}
    response = app_client.get("/v1.0/more-than-one-scope", headers=headers)
    assert response.status_code == 401

    # has all necessary scopes
    headers = {"Authorization": "Bearer has_myscope_otherscope"}
    response = app_client.get("/v1.0/more-than-one-scope", headers=headers)
    assert response.status_code == 200

    # has all necessary scopes but under key 'scopes'
    headers = {"Authorization": "Bearer has_scopes_in_scopes_with_s"}
    response = app_client.get("/v1.0/more-than-one-scope", headers=headers)
    assert response.status_code == 200


def test_security_with_strict_validation(secure_endpoint_strict_app):
    app_client = secure_endpoint_strict_app.test_client()

    res = app_client.get("/v1.0/test_apikey_query_parameter_validation")
    assert res.status_code == 401

    res = app_client.get(
        "/v1.0/test_apikey_query_parameter_validation",
        params={"name": "foo"},
    )
    assert res.status_code == 401

    res = app_client.get(
        "/v1.0/test_apikey_query_parameter_validation",
        params={"apikey": "mykey", "name": "foo"},
    )
    assert res.status_code == 200

    res = app_client.get(
        "/v1.0/test_apikey_query_parameter_validation",
        params={"apikey": "mykey", "name": "foo", "extra_param": "bar"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Extra query parameter(s) extra_param not in spec"


def test_security_map(secure_api_spec_dir, spec):
    class MyBasicSecurityHandler(BasicSecurityHandler):
        """Uses my_basic instead of basic as auth type."""

        def _get_verify_func(self, basic_info_func):
            check_basic_info_func = self.check_basic_auth(basic_info_func)

            def wrapper(request):
                auth_type, user_pass = self.get_auth_header_value(request)
                if auth_type != "my_basic":
                    return NO_VALUE

                try:
                    username, password = (
                        base64.b64decode(user_pass).decode("latin1").split(":", 1)
                    )
                except Exception:
                    raise OAuthProblem(detail="Invalid authorization header")

                return check_basic_info_func(request, username, password)

            return wrapper

    security_map = {
        "basic": MyBasicSecurityHandler,
    }
    # api level
    app = App(__name__, specification_dir=secure_api_spec_dir)
    app.add_api(spec, security_map=security_map)
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/greeting_basic/",
        headers={"Authorization": "basic dGVzdDp0ZXN0"},
    )
    assert res.status_code == 401

    res = app_client.post(
        "/v1.0/greeting_basic",
        headers={"Authorization": "my_basic dGVzdDp0ZXN0"},
    )
    assert res.status_code == 200

    # app level
    app = App(
        __name__, specification_dir=secure_api_spec_dir, security_map=security_map
    )
    app.add_api(spec)
    app_client = app.test_client()

    res = app_client.post(
        "/v1.0/greeting_basic/",
        headers={"Authorization": "basic dGVzdDp0ZXN0"},
    )
    assert res.status_code == 401

    res = app_client.post(
        "/v1.0/greeting_basic",
        headers={"Authorization": "my_basic dGVzdDp0ZXN0"},
    )
    assert res.status_code == 200
