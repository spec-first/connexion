import json
from struct import unpack

from connexion.decorators.produces import JSONEncoder


def test_app(simple_app):
    assert simple_app.port == 5001

    app_client = simple_app.app.test_client()
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 200
    assert b"Swagger UI" in swagger_ui.data

    swagger_icon = app_client.get('/v1.0/ui/images/favicon.ico')  # type: flask.Response
    assert swagger_icon.status_code == 200

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'


def test_produce_decorator(simple_app):
    app_client = simple_app.app.test_client()

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.content_type == 'text/plain; charset=utf-8'


def test_jsonifier(simple_app):
    app_client = simple_app.app.test_client()

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'

    get_list_greeting = app_client.get('/v1.0/list/jsantos', data={})  # type: flask.Response
    assert get_list_greeting.status_code == 200
    assert get_list_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(get_list_greeting.data.decode('utf-8'))
    assert len(greeting_reponse) == 2
    assert greeting_reponse[0] == 'hello'
    assert greeting_reponse[1] == 'jsantos'

    get_greetings = app_client.get('/v1.0/greetings/jsantos', data={})  # type: flask.Response
    assert get_greetings.status_code == 200
    assert get_greetings.content_type == 'application/x.connexion+json'
    greetings_reponse = json.loads(get_greetings.data.decode('utf-8'))
    assert len(greetings_reponse) == 1
    assert greetings_reponse['greetings'] == 'Hello jsantos'


def test_not_content_response(simple_app):
    app_client = simple_app.app.test_client()

    get_no_content_response = app_client.get('/v1.0/test_no_content_response')
    assert get_no_content_response.status_code == 204
    assert get_no_content_response.content_length == 0


def test_pass_through(simple_app):
    app_client = simple_app.app.test_client()

    response = app_client.get('/v1.0/multimime', data={})  # type: flask.Response
    assert response.status_code == 200


def test_empty(simple_app):
    app_client = simple_app.app.test_client()

    response = app_client.get('/v1.0/empty')  # type: flask.Response
    assert response.status_code == 204
    assert not response.data


def test_redirect_endpoint(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-redirect-endpoint')
    assert resp.status_code == 302


def test_redirect_response_endpoint(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-redirect-response-endpoint')
    assert resp.status_code == 302


def test_default_object_body(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-default-object-body')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response['stack'] == {'image_version': 'default_image'}

    resp = app_client.post('/v1.0/test-default-integer-body')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 1


def test_custom_encoder(simple_app):

    class CustomEncoder(JSONEncoder):
        def default(self, o):
            if o.__class__.__name__ == 'DummyClass':
                return "cool result"
            return JSONEncoder.default(self, o)

    flask_app = simple_app.app
    flask_app.json_encoder = CustomEncoder
    app_client = flask_app.test_client()

    resp = app_client.get('/v1.0/custom-json-response')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response['theResult'] == 'cool result'


def test_content_type_not_json(simple_app):
    app_client = simple_app.app.test_client()

    resp = app_client.get('/v1.0/blob-response')
    assert resp.status_code == 200

    # validate binary content
    text, number = unpack('!4sh', resp.data)
    assert text == b'cool'
    assert number == 8


def test_maybe_blob_or_json(simple_app):
    app_client = simple_app.app.test_client()

    resp = app_client.get('/v1.0/binary-response')
    assert resp.status_code == 200
    assert resp.content_type == 'application/octet-stream'
    # validate binary content
    text, number = unpack('!4sh', resp.data)
    assert text == b'cool'
    assert number == 8


def test_bad_operations(bad_operations_app):
    # Bad operationIds in bad_operations_app should result in 501
    app_client = bad_operations_app.app.test_client()

    resp = app_client.get('/v1.0/welcome')
    assert resp.status_code == 501

    resp = app_client.put('/v1.0/welcome')
    assert resp.status_code == 501

    resp = app_client.post('/v1.0/welcome')
    assert resp.status_code == 501


def test_text_request(simple_app):
    app_client = simple_app.app.test_client()

    resp = app_client.post('/v1.0/text-request', data=u'text')
    assert resp.status_code == 200
    assert resp.content_type == 'text/plain; charset=utf-8'
    # validate text content
    assert resp.data == u'text'
