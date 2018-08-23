import json
from struct import unpack

from werkzeug.test import Client, EnvironBuilder

from connexion.apps.flask_app import FlaskJSONEncoder


def test_app(simple_app):
    assert simple_app.port == 5001

    app_client = simple_app.app.test_client()

    # by default the Swagger UI is enabled
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 200
    assert b"Swagger UI" in swagger_ui.data

    # test return Swagger UI static files
    swagger_icon = app_client.get('/v1.0/ui/swagger-ui.js')  # type: flask.Response
    assert swagger_icon.status_code == 200

    post_greeting_url = app_client.post('/v1.0/greeting/jsantos/the/third/of/his/name', data={})  # type: flask.Response
    assert post_greeting_url.status_code == 200
    assert post_greeting_url.content_type == 'application/json'
    greeting_response_url = json.loads(post_greeting_url.data.decode('utf-8'))
    assert greeting_response_url['greeting'] == 'Hello jsantos thanks for the/third/of/his/name'

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_response = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_response['greeting'] == 'Hello jsantos'

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_response = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_response['greeting'] == 'Hello jsantos'


def test_produce_decorator(simple_app):
    app_client = simple_app.app.test_client()

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.content_type == 'text/plain; charset=utf-8'


def test_returning_flask_response_tuple(simple_app):
    app_client = simple_app.app.test_client()

    result = app_client.get('/v1.0/flask_response_tuple')  # type: flask.Response
    assert result.status_code == 201
    assert result.content_type == 'application/json'
    result_data = json.loads(result.data.decode('utf-8', 'replace'))
    assert result_data == {'foo': 'bar'}


def test_jsonifier(simple_app):
    app_client = simple_app.app.test_client()

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8', 'replace'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'

    get_list_greeting = app_client.get('/v1.0/list/jsantos', data={})  # type: flask.Response
    assert get_list_greeting.status_code == 200
    assert get_list_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(get_list_greeting.data.decode('utf-8', 'replace'))
    assert len(greeting_reponse) == 2
    assert greeting_reponse[0] == 'hello'
    assert greeting_reponse[1] == 'jsantos'

    get_greetings = app_client.get('/v1.0/greetings/jsantos', data={})  # type: flask.Response
    assert get_greetings.status_code == 200
    assert get_greetings.content_type == 'application/x.connexion+json'
    greetings_reponse = json.loads(get_greetings.data.decode('utf-8', 'replace'))
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
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response['stack'] == {'image_version': 'default_image'}

    resp = app_client.post('/v1.0/test-default-integer-body')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response == 1


def test_custom_encoder(simple_app):

    class CustomEncoder(FlaskJSONEncoder):
        def default(self, o):
            if o.__class__.__name__ == 'DummyClass':
                return "cool result"
            return FlaskJSONEncoder.default(self, o)

    flask_app = simple_app.app
    flask_app.json_encoder = CustomEncoder
    app_client = flask_app.test_client()

    resp = app_client.get('/v1.0/custom-json-response')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
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

    resp = app_client.post('/v1.0/text-request', data='text')
    assert resp.status_code == 200


def test_operation_handler_returns_flask_object(invalid_resp_allowed_app):
    app_client = invalid_resp_allowed_app.app.test_client()
    resp = app_client.get('/v1.0/get_non_conforming_response')
    assert resp.status_code == 200


def test_post_wrong_content_type(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/post_wrong_content_type',
                           content_type="application/xml",
                           data=json.dumps({"some": "data"})
                           )
    assert resp.status_code == 415

    resp = app_client.post('/v1.0/post_wrong_content_type',
                           data=json.dumps({"some": "data"})
                           )
    assert resp.status_code == 415

    # this test checks exactly what the test directly above is supposed to check,
    # i.e. no content-type is provided in the header
    # unfortunately there is an issue with the werkzeug test environment
    # (https://github.com/pallets/werkzeug/issues/1159)
    # so that content-type is added to every request, we remove it here manually for our test
    # this test can be removed once the werkzeug issue is addressed
    builder = EnvironBuilder(path='/v1.0/post_wrong_content_type', method='POST',
                             data=json.dumps({"some": "data"}))
    try:
        environ = builder.get_environ()
    finally:
        builder.close()
    environ.pop('CONTENT_TYPE')
    # we cannot just call app_client.open() since app_client is a flask.testing.FlaskClient
    # which overrides werkzeug.test.Client.open() but does not allow passing an environment
    # directly
    resp = Client.open(app_client, environ)
    assert resp.status_code == 415


    resp = app_client.post('/v1.0/post_wrong_content_type',
                           content_type="application/json",
                           data="not a valid json"
                           )
    assert resp.status_code == 400, \
        "Should return 400 when Content-Type is json but content not parsable"


def test_get_unicode_response(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/get_unicode_response')
    actualJson = {u'currency': u'\xa3', u'key': u'leena'}
    assert json.loads(resp.data.decode('utf-8','replace')) == actualJson


def test_get_enum_response(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/get_enum_response')
    assert resp.status_code == 200

def test_get_httpstatus_response(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/get_httpstatus_response')
    assert resp.status_code == 200


def test_get_bad_default_response(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/get_bad_default_response/200')
    assert resp.status_code == 200

    resp = app_client.get('/v1.0/get_bad_default_response/202')
    assert resp.status_code == 500
