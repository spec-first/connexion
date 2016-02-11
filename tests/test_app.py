import pathlib
import json
import logging
import pytest
from connexion.app import App

logging.basicConfig(level=logging.DEBUG)

TEST_FOLDER = pathlib.Path(__file__).parent
SPEC_FOLDER = TEST_FOLDER / "fakeapi"


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
    def fake_get(url, params=None, timeout=None):
        """
        :type url: str
        :type params: dict| None
        """
        params = params or {}
        if url == "https://ouath.example/token_info":
            token = params['access_token']
            if token == "100":
                return FakeResponse(200, '{"uid": "test-user", "scope": ["myscope"]}')
            if token == "200":
                return FakeResponse(200, '{"uid": "test-user", "scope": ["wrongscope"]}')
            if token == "300":
                return FakeResponse(404, '')
        return url

    monkeypatch.setattr('connexion.decorators.security.session.get', fake_get)


@pytest.fixture
def app():
    app = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app.add_api('api.yaml', validate_responses=True)
    return app


def test_add_api_with_function_resolver_function_is_wrapped():
    app = App(__name__, specification_dir=SPEC_FOLDER)
    api = app.add_api('api.yaml', resolver=lambda oid: (lambda foo: 'bar'))
    assert api.resolver.resolve_function_from_operation_id('faux')('bah') == 'bar'


def test_app_with_relative_path():
    # Create the app with a realative path and run the test_app testcase below.
    app = App(__name__, 5001, SPEC_FOLDER.relative_to(TEST_FOLDER),
              debug=True)
    app.add_api('api.yaml')
    test_app(app)


def test_app(app):
    assert app.port == 5001

    app_client = app.app.test_client()
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


def test_no_swagger():
    app = App(__name__, 5001, SPEC_FOLDER, swagger_ui=False, debug=True)
    app.add_api('api.yaml')
    app_client = app.app.test_client()
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 404

    app2 = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app2.add_api('api.yaml', swagger_ui=False)
    app2_client = app2.app.test_client()
    swagger_ui2 = app2_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui2.status_code == 404


def test_produce_decorator(app):
    app_client = app.app.test_client()

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.content_type == 'text/plain; charset=utf-8'


def test_errors(app):
    app_client = app.app.test_client()

    greeting404 = app_client.get('/v1.0/greeting')  # type: flask.Response
    assert greeting404.content_type == 'application/problem+json'
    assert greeting404.status_code == 404
    error404 = json.loads(greeting404.data.decode('utf-8'))
    assert error404['type'] == 'about:blank'
    assert error404['title'] == 'Not Found'
    assert error404['detail'] == 'The requested URL was not found on the server.  ' \
                                 'If you entered the URL manually please check your spelling and try again.'
    assert error404['status'] == 404
    assert 'instance' not in error404

    get_greeting = app_client.get('/v1.0/greeting/jsantos')  # type: flask.Response
    assert get_greeting.content_type == 'application/problem+json'
    assert get_greeting.status_code == 405
    error405 = json.loads(get_greeting.data.decode('utf-8'))
    assert error405['type'] == 'about:blank'
    assert error405['title'] == 'Method Not Allowed'
    assert error405['detail'] == 'The method is not allowed for the requested URL.'
    assert error405['status'] == 405
    assert 'instance' not in error405

    get500 = app_client.get('/v1.0/except')  # type: flask.Response
    assert get500.content_type == 'application/problem+json'
    assert get500.status_code == 500
    error500 = json.loads(get500.data.decode('utf-8'))
    assert error500['type'] == 'about:blank'
    assert error500['title'] == 'Internal Server Error'
    assert error500['detail'] == 'The server encountered an internal error and was unable to complete your request.  ' \
                                 'Either the server is overloaded or there is an error in the application.'
    assert error500['status'] == 500
    assert 'instance' not in error500

    get_problem = app_client.get('/v1.0/problem')  # type: flask.Response
    assert get_problem.content_type == 'application/problem+json'
    assert get_problem.status_code == 418
    assert get_problem.headers['x-Test-Header'] == 'In Test'
    error_problem = json.loads(get_problem.data.decode('utf-8'))
    assert error_problem['type'] == 'http://www.example.com/error'
    assert error_problem['title'] == 'Some Error'
    assert error_problem['detail'] == 'Something went wrong somewhere'
    assert error_problem['status'] == 418
    assert error_problem['instance'] == 'instance1'

    get_problem2 = app_client.get('/v1.0/other_problem')  # type: flask.Response
    assert get_problem2.content_type == 'application/problem+json'
    assert get_problem2.status_code == 418
    error_problem2 = json.loads(get_problem2.data.decode('utf-8'))
    assert error_problem2['type'] == 'about:blank'
    assert error_problem2['title'] == 'Some Error'
    assert error_problem2['detail'] == 'Something went wrong somewhere'
    assert error_problem2['status'] == 418
    assert error_problem2['instance'] == 'instance1'


def test_jsonifier(app):
    app_client = app.app.test_client()

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


def test_headers_jsonifier(app):
    app_client = app.app.test_client()

    response = app_client.post('/v1.0/goodday/dan', data={})  # type: flask.Response
    assert response.status_code == 201
    assert response.headers["Location"] == "http://localhost/my/uri"


def test_headers_produces(app):
    app_client = app.app.test_client()

    response = app_client.post('/v1.0/goodevening/dan', data={})  # type: flask.Response
    assert response.status_code == 201
    assert response.headers["Location"] == "http://localhost/my/uri"


def test_header_not_returned(app):
    app_client = app.app.test_client()

    response = app_client.post('/v1.0/goodday/noheader', data={})  # type: flask.Response
    assert response.content_type == 'application/problem+json'
    assert response.status_code == 500  # view_func has not returned what was promised in spec
    data = json.loads(response.data.decode('utf-8'))
    assert data['type'] == 'about:blank'
    assert data['title'] == 'Internal Server Error'
    assert data['detail'] == 'Response headers do not conform to specification'
    assert data['status'] == 500


def test_not_content_response(app):
    app_client = app.app.test_client()

    get_no_content_response = app_client.get('/v1.0/test_no_content_response')
    assert get_no_content_response.status_code == 204
    assert get_no_content_response.content_length == 0


def test_pass_through(app):
    app_client = app.app.test_client()

    response = app_client.get('/v1.0/multimime', data={})  # type: flask.Response
    assert response.status_code == 200


def test_security(oauth_requests):
    app1 = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app1.add_api('api.yaml')
    assert app1.port == 5001

    app_client = app1.app.test_client()
    get_bye_no_auth = app_client.get('/v1.0/byesecure/jsantos')  # type: flask.Response
    assert get_bye_no_auth.status_code == 401
    assert get_bye_no_auth.content_type == 'application/problem+json'
    get_bye_no_auth_reponse = json.loads(get_bye_no_auth.data.decode())  # type: dict
    assert get_bye_no_auth_reponse['title'] == 'Unauthorized'
    assert get_bye_no_auth_reponse['detail'] == "No authorization token provided"

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.data == b'Goodbye jsantos (Secure: test-user)'

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 200"}
    get_bye_wrong_scope = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_wrong_scope.status_code == 403
    assert get_bye_wrong_scope.content_type == 'application/problem+json'
    get_bye_wrong_scope_reponse = json.loads(get_bye_wrong_scope.data.decode())  # type: dict
    assert get_bye_wrong_scope_reponse['title'] == 'Forbidden'
    assert get_bye_wrong_scope_reponse['detail'] == "Provided token doesn't have the required scope"

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_bye_bad_token = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_bad_token.status_code == 401
    assert get_bye_bad_token.content_type == 'application/problem+json'
    get_bye_bad_token_reponse = json.loads(get_bye_bad_token.data.decode())  # type: dict
    assert get_bye_bad_token_reponse['title'] == 'Unauthorized'
    assert get_bye_bad_token_reponse['detail'] == "Provided oauth token is not valid"


def test_empty(app):
    app_client = app.app.test_client()

    response = app_client.get('/v1.0/empty')  # type: flask.Response
    assert response.status_code == 204
    assert not response.data


def test_schema(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    empty_request = app_client.post('/v1.0/test_schema', headers=headers, data=json.dumps({}))  # type: flask.Response
    assert empty_request.status_code == 400
    assert empty_request.content_type == 'application/problem+json'
    empty_request_response = json.loads(empty_request.data.decode())  # type: dict
    assert empty_request_response['title'] == 'Bad Request'
    assert empty_request_response['detail'].startswith("'image_version' is a required property")

    bad_type = app_client.post('/v1.0/test_schema', headers=headers,
                               data=json.dumps({'image_version': 22}))  # type: flask.Response
    assert bad_type.status_code == 400
    assert bad_type.content_type == 'application/problem+json'
    bad_type_response = json.loads(bad_type.data.decode())  # type: dict
    assert bad_type_response['title'] == 'Bad Request'
    assert bad_type_response['detail'].startswith("22 is not of type 'string'")

    good_request = app_client.post('/v1.0/test_schema', headers=headers,
                                   data=json.dumps({'image_version': 'version'}))  # type: flask.Response
    assert good_request.status_code == 200
    good_request_response = json.loads(good_request.data.decode())  # type: dict
    assert good_request_response['image_version'] == 'version'

    good_request_extra = app_client.post('/v1.0/test_schema', headers=headers,
                                         data=json.dumps({'image_version': 'version',
                                                          'extra': 'stuff'}))  # type: flask.Response
    assert good_request_extra.status_code == 200
    good_request_extra_response = json.loads(good_request.data.decode())  # type: dict
    assert good_request_extra_response['image_version'] == 'version'

    wrong_type = app_client.post('/v1.0/test_schema', headers=headers, data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode())  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'object'")


def test_schema_response(app):
    app_client = app.app.test_client()

    request = app_client.get('/v1.0/test_schema/response/object/valid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 200
    request = app_client.get('/v1.0/test_schema/response/object/invalid_type', headers={},
                             data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/object/invalid_requirements', headers={},
                             data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/string/valid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 200
    request = app_client.get('/v1.0/test_schema/response/string/invalid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/integer/valid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 200
    request = app_client.get('/v1.0/test_schema/response/integer/invalid', headers={},
                             data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/number/valid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 200
    request = app_client.get('/v1.0/test_schema/response/number/invalid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/boolean/valid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 200
    request = app_client.get('/v1.0/test_schema/response/boolean/invalid', headers={},
                             data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/array/valid', headers={}, data=None)  # type: flask.Response
    assert request.status_code == 200
    request = app_client.get('/v1.0/test_schema/response/array/invalid_dict', headers={},
                             data=None)  # type: flask.Response
    assert request.status_code == 500
    request = app_client.get('/v1.0/test_schema/response/array/invalid_string', headers={},
                             data=None)  # type: flask.Response
    assert request.status_code == 500


def test_schema_in_query(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    good_request = app_client.post('/v1.0/test_schema_in_query', headers=headers,
                                   query_string={'image_version': 'version',
                                                 'not_required': 'test'})  # type: flask.Response
    assert good_request.status_code == 200
    good_request_response = json.loads(good_request.data.decode())  # type: dict
    assert good_request_response['image_version'] == 'version'


def test_schema_list(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    wrong_type = app_client.post('/v1.0/test_schema_list', headers=headers, data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode())  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'array'")

    wrong_items = app_client.post('/v1.0/test_schema_list', headers=headers,
                                  data=json.dumps([42]))  # type: flask.Response
    assert wrong_items.status_code == 400
    assert wrong_items.content_type == 'application/problem+json'
    wrong_items_response = json.loads(wrong_items.data.decode())  # type: dict
    assert wrong_items_response['title'] == 'Bad Request'
    assert wrong_items_response['detail'].startswith("42 is not of type 'string'")


def test_schema_map(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    valid_object = {
        "foo": {
            "image_version": "string"
        },
        "bar": {
            "image_version": "string"
        }
    }

    invalid_object = {
        "foo": 42
    }

    wrong_type = app_client.post('/v1.0/test_schema_map', headers=headers, data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode())  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'object'")

    wrong_items = app_client.post('/v1.0/test_schema_map', headers=headers,
                                  data=json.dumps(invalid_object))  # type: flask.Response
    assert wrong_items.status_code == 400
    assert wrong_items.content_type == 'application/problem+json'
    wrong_items_response = json.loads(wrong_items.data.decode())  # type: dict
    assert wrong_items_response['title'] == 'Bad Request'
    assert wrong_items_response['detail'].startswith("42 is not of type 'object'")

    right_type = app_client.post('/v1.0/test_schema_map', headers=headers,
                                  data=json.dumps(valid_object))  # type: flask.Response
    assert right_type.status_code == 200


def test_schema_recursive(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    valid_object = {
        "children": [
            {"children": []},
            {"children": [
                {"children": []},
            ]},
            {"children": []},
        ]
    }

    invalid_object = {
        "children": [42]
    }

    wrong_type = app_client.post('/v1.0/test_schema_recursive', headers=headers, data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode())  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'object'")

    wrong_items = app_client.post('/v1.0/test_schema_recursive', headers=headers,
                                  data=json.dumps(invalid_object))  # type: flask.Response
    assert wrong_items.status_code == 400
    assert wrong_items.content_type == 'application/problem+json'
    wrong_items_response = json.loads(wrong_items.data.decode())  # type: dict
    assert wrong_items_response['title'] == 'Bad Request'
    assert wrong_items_response['detail'].startswith("42 is not of type 'object'")

    right_type = app_client.post('/v1.0/test_schema_recursive', headers=headers,
                                  data=json.dumps(valid_object))  # type: flask.Response
    assert right_type.status_code == 200


def test_schema_format(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    wrong_type = app_client.post('/v1.0/test_schema_format', headers=headers,
                                 data=json.dumps("xy"))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode())  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert "'xy' is not a 'date-time'" in wrong_type_response['detail']


def test_single_route(app):
    def route1():
        return 'single 1'

    @app.route('/single2', methods=['POST'])
    def route2():
        return 'single 2'

    app_client = app.app.test_client()

    app.add_url_rule('/single1', 'single1', route1, methods=['GET'])

    get_single1 = app_client.get('/single1')  # type: flask.Response
    assert get_single1.data == b'single 1'

    post_single1 = app_client.post('/single1')  # type: flask.Response
    assert post_single1.status_code == 405

    post_single2 = app_client.post('/single2')  # type: flask.Response
    assert post_single2.data == b'single 2'

    get_single2 = app_client.get('/single2')  # type: flask.Response
    assert get_single2.status_code == 405


def test_parameter_validation(app):
    app_client = app.app.test_client()

    url = '/v1.0/test_parameter_validation'

    response = app_client.get(url, query_string={'date': '2015-08-26'})  # type: flask.Response
    assert response.status_code == 200

    for invalid_int in '', 'foo', '0.1':
        response = app_client.get(url, query_string={'int': invalid_int})  # type: flask.Response
        assert response.status_code == 400

    response = app_client.get(url, query_string={'int': '123'})  # type: flask.Response
    assert response.status_code == 200

    for invalid_bool in '', 'foo', 'yes':
        response = app_client.get(url, query_string={'bool': invalid_bool})  # type: flask.Response
        assert response.status_code == 400

    response = app_client.get(url, query_string={'bool': 'true'})  # type: flask.Response
    assert response.status_code == 200


def test_required_query_param(app):
    app_client = app.app.test_client()

    url = '/v1.0/test_required_query_param'
    response = app_client.get(url)
    assert response.status_code == 400

    response = app_client.get(url, query_string={'n': '1.23'})
    assert response.status_code == 200


def test_array_query_param(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}
    url = '/v1.0/test_array_csv_query_param?items=one,two,three'
    response = app_client.get(url, headers=headers)
    array_response = json.loads(response.data.decode())  # type: [str]
    assert array_response == ['one', 'two', 'three']
    url = '/v1.0/test_array_pipes_query_param?items=1|2|3'
    response = app_client.get(url, headers=headers)
    array_response = json.loads(response.data.decode())  # type: [int]
    assert array_response == [1, 2, 3]
    url = '/v1.0/test_array_unsupported_query_param?items=1;2;3'
    response = app_client.get(url, headers=headers)
    array_response = json.loads(response.data.decode())  # [str] unsupported collectionFormat
    assert array_response == ["1;2;3"]


def test_test_schema_array(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    array_request = app_client.get('/v1.0/schema_array', headers=headers,
                                   data=json.dumps(['list', 'hello']))  # type: flask.Response
    assert array_request.status_code == 200
    assert array_request.content_type == 'application/json'
    array_response = json.loads(array_request.data.decode())  # type: list
    assert array_response == ['list', 'hello']


def test_test_schema_int(app):
    app_client = app.app.test_client()
    headers = {'Content-type': 'application/json'}

    array_request = app_client.get('/v1.0/schema_int', headers=headers,
                                   data=json.dumps(42))  # type: flask.Response
    assert array_request.status_code == 200
    assert array_request.content_type == 'application/json'
    array_response = json.loads(array_request.data.decode())  # type: list
    assert array_response == 42


def test_resolve_method(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/resolver-test/method')  # type: flask.Response
    assert resp.data.decode() == '"DummyClass"'


def test_resolve_classmethod(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/resolver-test/classmethod')  # type: flask.Response
    assert resp.data.decode() == '"DummyClass"'


def test_path_parameter_someint(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-int-path/123')  # type: flask.Response
    assert resp.data.decode() == '"int"'

    # non-integer values will not match Flask route
    resp = app_client.get('/v1.0/test-int-path/foo')  # type: flask.Response
    assert resp.status_code == 404


def test_path_parameter_somefloat(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-float-path/123.45')  # type: flask.Response
    assert resp.data.decode() == '"float"'

    # non-float values will not match Flask route
    resp = app_client.get('/v1.0/test-float-path/123,45')  # type: flask.Response
    assert resp.status_code == 404


def test_default_param(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-default-query-parameter')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response['app_name'] == 'connexion'


def test_default_object_body(app):
    app_client = app.app.test_client()
    resp = app_client.post('/v1.0/test-default-object-body')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response['stack'] == {'image_version': 'default_image'}

    resp = app_client.post('/v1.0/test-default-integer-body')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 1


def test_falsy_param(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-falsy-param', query_string={'falsy': 0})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 0

    resp = app_client.get('/v1.0/test-falsy-param')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 1


def test_formData_param(app):
    app_client = app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param', data={'formData': 'test'})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 'test'


def test_formData_missing_param(app):
    app_client = app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-missing-param', data={'missing_formData': 'test'})
    assert resp.status_code == 200


def test_bool_as_default_param(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-param')
    assert resp.status_code == 200

    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': True})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is True


def test_bool_param(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': True})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is True

    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': False})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is False


def test_bool_array_param(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param?thruthiness=true,true,true')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is True

    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param?thruthiness=true,true,false')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is False


def test_required_param_miss_config(app):
    app_client = app.app.test_client()

    resp = app_client.get('/v1.0/test-required-param')
    assert resp.status_code == 400

    resp = app_client.get('/v1.0/test-required-param', query_string={'simple': 'test'})
    assert resp.status_code == 200

    resp = app_client.get('/v1.0/test-required-param')
    assert resp.status_code == 400


def test_redirect_endpoint(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-redirect-endpoint')
    assert resp.status_code == 302


def test_redirect_response_endpoint(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-redirect-response-endpoint')
    assert resp.status_code == 302


def test_security_over_inexistent_endpoints(oauth_requests):
    app1 = App(__name__, 5001, SPEC_FOLDER, swagger_ui=False, debug=True, auth_all_paths=True)
    app1.add_api('secure_api.yaml')
    assert app1.port == 5001

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_inexistent_endpoint = app_client.get('/v1.0/does-not-exist-invalid-token', headers=headers)  # type: flask.Response
    assert get_inexistent_endpoint.status_code == 401
    assert get_inexistent_endpoint.content_type == 'application/problem+json'

    headers = {"Authorization": "Bearer 100"}
    get_inexistent_endpoint = app_client.get('/v1.0/does-not-exist-valid-token', headers=headers)  # type: flask.Response
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


def test_no_content_response_have_headers(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-204-with-headers')
    assert resp.status_code == 204
    assert 'X-Something' in resp.headers


def test_no_content_object_and_have_headers(app):
    app_client = app.app.test_client()
    resp = app_client.get('/v1.0/test-204-with-headers-nocontent-obj')
    assert resp.status_code == 204
    assert 'X-Something' in resp.headers
