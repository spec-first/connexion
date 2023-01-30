import json

import pytest
from connexion.security import SecurityHandlerFactory


class FakeResponse:
    def __init__(self, status_code, text):
        """
        :type status_code: int
        :type text: ste
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

    monkeypatch.setattr(SecurityHandlerFactory, "client", FakeClient())


def test_security_over_nonexistent_endpoints(oauth_requests, secure_api_app):
    app_client = secure_api_app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_inexistent_endpoint = app_client.get(
        "/v1.0/does-not-exist-invalid-token", headers=headers
    )  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 401
    assert get_inexistent_endpoint.content_type == "application/problem+json"

    headers = {"Authorization": "Bearer 100"}
    get_inexistent_endpoint = app_client.get(
        "/v1.0/does-not-exist-valid-token", headers=headers
    )  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 404
    assert get_inexistent_endpoint.content_type == "application/problem+json"

    get_inexistent_endpoint = app_client.get(
        "/v1.0/does-not-exist-no-token"
    )  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 401

    headers = {"Authorization": "Bearer 100"}
    post_greeting = app_client.post(
        "/v1.0/greeting/rcaricio", data={}, headers=headers
    )  # type: flask.Response
    assert post_greeting.status_code == 200

    post_greeting = app_client.post(
        "/v1.0/greeting/rcaricio", data={}
    )  # type: flask.Response
    assert post_greeting.status_code == 401


def test_security(oauth_requests, secure_endpoint_app):
    app_client = secure_endpoint_app.test_client()

    get_bye_no_auth = app_client.get("/v1.0/byesecure/jsantos")  # type: flask.Response
    assert get_bye_no_auth.status_code == 401
    assert get_bye_no_auth.content_type == "application/problem+json"
    get_bye_no_auth_reponse = json.loads(
        get_bye_no_auth.data.decode("utf-8", "replace")
    )  # type: dict
    assert get_bye_no_auth_reponse["detail"] == "No authorization token provided"

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get(
        "/v1.0/byesecure/jsantos", headers=headers
    )  # type: flask.Response
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.data == b"Goodbye jsantos (Secure: test-user)"

    headers = {"Authorization": "Bearer 200"}
    get_bye_wrong_scope = app_client.get(
        "/v1.0/byesecure/jsantos", headers=headers
    )  # type: flask.Response
    assert get_bye_wrong_scope.status_code == 403
    assert get_bye_wrong_scope.content_type == "application/problem+json"
    get_bye_wrong_scope_reponse = json.loads(
        get_bye_wrong_scope.data.decode("utf-8", "replace")
    )  # type: dict
    assert (
        get_bye_wrong_scope_reponse["detail"]
        == "Provided token doesn't have the required scope"
    )

    headers = {"Authorization": "Bearer 300"}
    get_bye_bad_token = app_client.get(
        "/v1.0/byesecure/jsantos", headers=headers
    )  # type: flask.Response
    assert get_bye_bad_token.status_code == 401
    assert get_bye_bad_token.content_type == "application/problem+json"
    get_bye_bad_token_reponse = json.loads(
        get_bye_bad_token.data.decode("utf-8", "replace")
    )  # type: dict
    assert get_bye_bad_token_reponse["detail"] == "Provided token is not valid"

    response = app_client.get(
        "/v1.0/more-than-one-security-definition"
    )  # type: flask.Response
    assert response.status_code == 401

    # also tests case-insensitivity
    headers = {"X-AUTH": "mykey"}
    response = app_client.get(
        "/v1.0/more-than-one-security-definition", headers=headers
    )  # type: flask.Response
    assert response.status_code == 200

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get(
        "/v1.0/byesecure-ignoring-context/hjacobs", headers=headers
    )  # type: flask.Response
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.data == b"Goodbye hjacobs (Secure!)"

    headers = {"Authorization": "Bearer 100"}
    get_bye_from_flask = app_client.get(
        "/v1.0/byesecure-from-flask", headers=headers
    )  # type: flask.Response
    assert get_bye_from_flask.data == b"Goodbye test-user (Secure!)"

    headers = {"Authorization": "Bearer 100"}
    get_bye_from_connexion = app_client.get(
        "/v1.0/byesecure-from-connexion", headers=headers
    )  # type: flask.Response
    assert get_bye_from_connexion.data == b"Goodbye test-user (Secure!)"

    headers = {"Authorization": "Bearer 100"}
    get_bye_from_connexion = app_client.get(
        "/v1.0/byesecure-jwt/test-user", headers=headers
    )  # type: flask.Response
    assert get_bye_from_connexion.data == b"Goodbye test-user (Secure: 100)"

    # has optional auth
    response = app_client.get("/v1.0/optional-auth")  # type: flask.Response
    assert response.status_code == 200
    assert response.data == b'"Unauthenticated"\n'
    headers = {"X-AUTH": "mykey"}
    response = app_client.get(
        "/v1.0/optional-auth", headers=headers
    )  # type: flask.Response
    assert response.status_code == 200
    assert response.data == b'"Authenticated"\n'
    headers = {"X-AUTH": "wrong-key"}
    response = app_client.get(
        "/v1.0/optional-auth", headers=headers
    )  # type: flask.Response
    assert response.data == b'"Unauthenticated"\n'
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
    response = app_client.get(
        "/v1.0/more-than-one-scope", headers=headers
    )  # type: flask.Response
    assert response.status_code == 403

    # has none of the necessary scopes
    headers = {"Authorization": "Bearer has_wrongscope"}
    response = app_client.get(
        "/v1.0/more-than-one-scope", headers=headers
    )  # type: flask.Response
    assert response.status_code == 403

    # is not auth
    headers = {"Authorization": "Bearer is_not_invalid"}
    response = app_client.get(
        "/v1.0/more-than-one-scope", headers=headers
    )  # type: flask.Response
    assert response.status_code == 401

    # has all necessary scopes
    headers = {"Authorization": "Bearer has_myscope_otherscope"}
    response = app_client.get(
        "/v1.0/more-than-one-scope", headers=headers
    )  # type: flask.Response
    assert response.status_code == 200

    # has all necessary scopes but under key 'scopes'
    headers = {"Authorization": "Bearer has_scopes_in_scopes_with_s"}
    response = app_client.get(
        "/v1.0/more-than-one-scope", headers=headers
    )  # type: flask.Response
    assert response.status_code == 200
