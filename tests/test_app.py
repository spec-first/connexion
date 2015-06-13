
import pathlib
import flask
import json

from connexion.app import App

TEST_FOLDER = pathlib.Path(__file__).parent
SPEC_FOLDER = TEST_FOLDER / "fakeapi"

def test_app():
    app1 = App(__name__, 5001, SPEC_FOLDER)
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

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={}) # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'