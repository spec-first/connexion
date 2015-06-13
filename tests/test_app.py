import pathlib
import flask
import json
import pytest
import requests
import logging
import _pytest.monkeypatch

from connexion.app import App

logging.basicConfig(level=logging.DEBUG)

TEST_FOLDER = pathlib.Path(__file__).parent
SPEC_FOLDER = TEST_FOLDER / "fakeapi"


class FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text
        self.ok = status_code == 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def oauth_requests(monkeypatch: '_pytest.monkeypatch.monkeypatch'):
    def fake_get(url:str, params:dict=None):
        params = params or {}
        if url == "https://ouath.example/token_info":
            token = params['access_token']
            if token == "100":
                return FakeResponse(200, '{"scope": ["myscope"]}')
            if token == "200":
                return FakeResponse(200, '{"scope": ["wrongscope"]}')
            if token == "300":
                return FakeResponse(404, '')
        return url

    monkeypatch.setattr(requests, 'get', fake_get)


def test_app():
    app1 = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app1.add_api('api.yaml')
    assert app1.port == 5001

    app_client = app1.app.test_client()
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 200
    assert b"Swagger UI" in swagger_ui.data

    swagger_icon = app_client.get('/v1.0/ui/images/favicon.ico')  # type: flask.Response
    assert swagger_icon.status_code == 200

    greeting404 = app_client.get('/v1.0/greeting')  # type: flask.Response
    assert greeting404.status_code == 404
    error404 = json.loads(greeting404.data.decode('utf-8'))
    assert error404['status_name'] == 'Not Found'
    assert error404['status_code'] == 404

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'

    get_greeting = app_client.get('/v1.0/greeting/jsantos')  # type: flask.Response
    assert get_greeting.status_code == 405
    assert get_greeting.content_type == 'application/json'

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'


def test_security(oauth_requests):
    app1 = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app1.add_api('api.yaml')
    assert app1.port == 5001

    app_client = app1.app.test_client()
    get_bye_no_auth = app_client.get('/v1.0/byesecure/jsantos')  # type: flask.Response
    assert get_bye_no_auth.status_code == 401

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.data == b'Goodbye jsantos (Secure)'

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 200"}
    get_bye_wrong_scope = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_wrong_scope.status_code == 401

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_bye_bad_token = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_bad_token.status_code == 401
