import json

from connexion import FlaskApp


def test_security_over_inexistent_endpoints(oauth_requests, secure_api_spec_dir):
    app1 = FlaskApp(__name__, 5001, secure_api_spec_dir, swagger_ui=False,
               debug=True, auth_all_paths=True)
    app1.add_api('swagger.yaml')
    assert app1.port == 5001

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_inexistent_endpoint = app_client.get('/v1.0/does-not-exist-invalid-token',
                                             headers=headers)  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 401
    assert get_inexistent_endpoint.content_type == 'application/problem+json'

    headers = {"Authorization": "Bearer 100"}
    get_inexistent_endpoint = app_client.get('/v1.0/does-not-exist-valid-token',
                                             headers=headers)  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 404
    assert get_inexistent_endpoint.content_type == 'application/problem+json'

    get_inexistent_endpoint = app_client.get('/v1.0/does-not-exist-no-token')  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 401

    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 401

    headers = {"Authorization": "Bearer 100"}
    post_greeting = app_client.post('/v1.0/greeting/rcaricio', data={}, headers=headers)  # type: flask.Response
    assert post_greeting.status_code == 200

    post_greeting = app_client.post('/v1.0/greeting/rcaricio', data={})  # type: flask.Response
    assert post_greeting.status_code == 401


def test_security(oauth_requests, secure_endpoint_app):
    app_client = secure_endpoint_app.app.test_client()

    get_bye_no_auth = app_client.get('/v1.0/byesecure/jsantos')  # type: flask.Response
    assert get_bye_no_auth.status_code == 401
    assert get_bye_no_auth.content_type == 'application/problem+json'
    get_bye_no_auth_reponse = json.loads(get_bye_no_auth.data.decode('utf-8', 'replace'))  # type: dict
    assert get_bye_no_auth_reponse['title'] == 'Unauthorized'
    assert get_bye_no_auth_reponse['detail'] == "No authorization token provided"

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.data == b'Goodbye jsantos (Secure: test-user)'

    headers = {"Authorization": "Bearer 200"}
    get_bye_wrong_scope = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_wrong_scope.status_code == 403
    assert get_bye_wrong_scope.content_type == 'application/problem+json'
    get_bye_wrong_scope_reponse = json.loads(get_bye_wrong_scope.data.decode('utf-8', 'replace'))  # type: dict
    assert get_bye_wrong_scope_reponse['title'] == 'Forbidden'
    assert get_bye_wrong_scope_reponse['detail'] == "Provided token doesn't have the required scope"

    headers = {"Authorization": "Bearer 300"}
    get_bye_bad_token = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_bad_token.status_code == 401
    assert get_bye_bad_token.content_type == 'application/problem+json'
    get_bye_bad_token_reponse = json.loads(get_bye_bad_token.data.decode('utf-8', 'replace'))  # type: dict
    assert get_bye_bad_token_reponse['title'] == 'Unauthorized'
    assert get_bye_bad_token_reponse['detail'] == "Provided oauth token is not valid"

    response = app_client.get('/v1.0/more-than-one-security-definition')  # type: flask.Response
    assert response.status_code == 200

    response = app_client.get('/v1.0/user-handled-security')  # type: flask.Response
    assert response.status_code == 200


def test_checking_that_client_token_has_all_necessary_scopes(
        oauth_requests, secure_endpoint_app):
    app_client = secure_endpoint_app.app.test_client()

    # has only one of the required scopes
    headers = {"Authorization": "Bearer has_myscope"}
    response = app_client.get('/v1.0/more-than-one-scope', headers=headers)  # type: flask.Response
    assert response.status_code == 403

    # has none of the necessary scopes
    headers = {"Authorization": "Bearer has_wrongscope"}
    response = app_client.get('/v1.0/more-than-one-scope', headers=headers)  # type: flask.Response
    assert response.status_code == 403

    # is not auth
    headers = {"Authorization": "Bearer is_not_invalid"}
    response = app_client.get('/v1.0/more-than-one-scope', headers=headers)  # type: flask.Response
    assert response.status_code == 401

    # has all necessary scopes
    headers = {"Authorization": "Bearer has_myscope_otherscope"}
    response = app_client.get('/v1.0/more-than-one-scope', headers=headers)  # type: flask.Response
    assert response.status_code == 200
