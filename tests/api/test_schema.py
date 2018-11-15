import json


def test_schema(schema_app):
    app_client = schema_app.app.test_client()
    headers = {'Content-type': 'application/json'}

    empty_request = app_client.post('/v1.0/test_schema', headers=headers, data=json.dumps({}))  # type: flask.Response
    assert empty_request.status_code == 400
    assert empty_request.content_type == 'application/problem+json'
    empty_request_response = json.loads(empty_request.data.decode('utf-8', 'replace'))  # type: dict
    assert empty_request_response['title'] == 'Bad Request'
    assert empty_request_response['detail'].startswith("'image_version' is a required property")

    bad_type = app_client.post('/v1.0/test_schema', headers=headers,
                               data=json.dumps({'image_version': 22}))  # type: flask.Response
    assert bad_type.status_code == 400
    assert bad_type.content_type == 'application/problem+json'
    bad_type_response = json.loads(bad_type.data.decode('utf-8', 'replace'))  # type: dict
    assert bad_type_response['title'] == 'Bad Request'
    assert bad_type_response['detail'].startswith("22 is not of type 'string'")

    good_request = app_client.post('/v1.0/test_schema', headers=headers,
                                   data=json.dumps({'image_version': 'version'}))  # type: flask.Response
    assert good_request.status_code == 200
    good_request_response = json.loads(good_request.data.decode('utf-8', 'replace'))  # type: dict
    assert good_request_response['image_version'] == 'version'

    good_request_extra = app_client.post('/v1.0/test_schema', headers=headers,
                                         data=json.dumps({'image_version': 'version',
                                                          'extra': 'stuff'}))  # type: flask.Response
    assert good_request_extra.status_code == 200
    good_request_extra_response = json.loads(good_request.data.decode('utf-8', 'replace'))  # type: dict
    assert good_request_extra_response['image_version'] == 'version'

    wrong_type = app_client.post('/v1.0/test_schema', headers=headers, data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode('utf-8', 'replace'))  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'object'")


def test_schema_response(schema_app):
    app_client = schema_app.app.test_client()

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


def test_schema_in_query(schema_app):
    app_client = schema_app.app.test_client()
    headers = {'Content-type': 'application/json'}

    good_request = app_client.post('/v1.0/test_schema_in_query', headers=headers,
                                   query_string={'image_version': 'version',
                                                 'not_required': 'test'})  # type: flask.Response
    assert good_request.status_code == 200
    good_request_response = json.loads(good_request.data.decode('utf-8', 'replace'))  # type: dict
    assert good_request_response['image_version'] == 'version'


def test_schema_list(schema_app):
    app_client = schema_app.app.test_client()
    headers = {'Content-type': 'application/json'}

    wrong_type = app_client.post('/v1.0/test_schema_list', headers=headers, data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode('utf-8', 'replace'))  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'array'")

    wrong_items = app_client.post('/v1.0/test_schema_list', headers=headers,
                                  data=json.dumps([42]))  # type: flask.Response
    assert wrong_items.status_code == 400
    assert wrong_items.content_type == 'application/problem+json'
    wrong_items_response = json.loads(wrong_items.data.decode('utf-8', 'replace'))  # type: dict
    assert wrong_items_response['title'] == 'Bad Request'
    assert wrong_items_response['detail'].startswith("42 is not of type 'string'")


def test_schema_map(schema_app):
    app_client = schema_app.app.test_client()
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
    wrong_type_response = json.loads(wrong_type.data.decode('utf-8', 'replace'))  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'object'")

    wrong_items = app_client.post('/v1.0/test_schema_map', headers=headers,
                                  data=json.dumps(invalid_object))  # type: flask.Response
    assert wrong_items.status_code == 400
    assert wrong_items.content_type == 'application/problem+json'
    wrong_items_response = json.loads(wrong_items.data.decode('utf-8', 'replace'))  # type: dict
    assert wrong_items_response['title'] == 'Bad Request'
    assert wrong_items_response['detail'].startswith("42 is not of type 'object'")

    right_type = app_client.post('/v1.0/test_schema_map', headers=headers,
                                 data=json.dumps(valid_object))  # type: flask.Response
    assert right_type.status_code == 200


def test_schema_recursive(schema_app):
    app_client = schema_app.app.test_client()
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

    wrong_type = app_client.post('/v1.0/test_schema_recursive', headers=headers,
                                 data=json.dumps(42))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode('utf-8'))  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert wrong_type_response['detail'].startswith("42 is not of type 'object'")

    wrong_items = app_client.post('/v1.0/test_schema_recursive', headers=headers,
                                  data=json.dumps(invalid_object))  # type: flask.Response
    assert wrong_items.status_code == 400
    assert wrong_items.content_type == 'application/problem+json'
    wrong_items_response = json.loads(wrong_items.data.decode('utf-8'))  # type: dict
    assert wrong_items_response['title'] == 'Bad Request'
    assert wrong_items_response['detail'].startswith("42 is not of type 'object'")

    right_type = app_client.post('/v1.0/test_schema_recursive', headers=headers,
                                 data=json.dumps(valid_object))  # type: flask.Response
    assert right_type.status_code == 200


def test_schema_format(schema_app):
    app_client = schema_app.app.test_client()
    headers = {'Content-type': 'application/json'}

    wrong_type = app_client.post('/v1.0/test_schema_format', headers=headers,
                                 data=json.dumps("xy"))  # type: flask.Response
    assert wrong_type.status_code == 400
    assert wrong_type.content_type == 'application/problem+json'
    wrong_type_response = json.loads(wrong_type.data.decode('utf-8', 'replace'))  # type: dict
    assert wrong_type_response['title'] == 'Bad Request'
    assert "'xy' is not a 'email'" in wrong_type_response['detail']


def test_schema_array(schema_app):
    app_client = schema_app.app.test_client()
    headers = {'Content-type': 'application/json'}

    array_request = app_client.post('/v1.0/schema_array', headers=headers,
                                    data=json.dumps(['list', 'hello']))  # type: flask.Response
    assert array_request.status_code == 200
    assert array_request.content_type == 'application/json'
    array_response = json.loads(array_request.data.decode('utf-8', 'replace'))  # type: list
    assert array_response == ['list', 'hello']


def test_schema_int(schema_app):
    app_client = schema_app.app.test_client()
    headers = {'Content-type': 'application/json'}

    array_request = app_client.post('/v1.0/schema_int', headers=headers,
                                    data=json.dumps(42))  # type: flask.Response
    assert array_request.status_code == 200
    assert array_request.content_type == 'application/json'
    array_response = json.loads(array_request.data.decode('utf-8', 'replace'))  # type: list
    assert array_response == 42


def test_global_response_definitions(schema_app):
    app_client = schema_app.app.test_client()
    resp = app_client.get('/v1.0/define_global_response')
    assert json.loads(resp.data.decode('utf-8', 'replace')) == ['general', 'list']
