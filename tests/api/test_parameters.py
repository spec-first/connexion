import json
from io import BytesIO
from typing import List

import pytest


def test_parameter_validation(simple_app):
    app_client = simple_app.app.test_client()

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


def test_required_query_param(simple_app):
    app_client = simple_app.app.test_client()

    url = '/v1.0/test_required_query_param'
    response = app_client.get(url)
    assert response.status_code == 400

    response = app_client.get(url, query_string={'n': '1.23'})
    assert response.status_code == 200


def test_array_query_param(simple_app):
    app_client = simple_app.app.test_client()
    headers = {'Content-type': 'application/json'}
    url = '/v1.0/test_array_csv_query_param'
    response = app_client.get(url, headers=headers)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))
    assert array_response == ['squash', 'banana']
    url = '/v1.0/test_array_csv_query_param?items=one,two,three'
    response = app_client.get(url, headers=headers)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))
    assert array_response == ['one', 'two', 'three']
    url = '/v1.0/test_array_pipes_query_param?items=1|2|3'
    response = app_client.get(url, headers=headers)
    array_response: List[int] = json.loads(response.data.decode('utf-8', 'replace'))
    assert array_response == [1, 2, 3]
    url = '/v1.0/test_array_unsupported_query_param?items=1;2;3'
    response = app_client.get(url, headers=headers)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))  # unsupported collectionFormat
    assert array_response == ["1;2;3"]
    url = '/v1.0/test_array_csv_query_param?items=A&items=B&items=C&items=D,E,F'
    response = app_client.get(url, headers=headers)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))  # multi array with csv format
    assert array_response == ['D', 'E', 'F']
    url = '/v1.0/test_array_multi_query_param?items=A&items=B&items=C&items=D,E,F'
    response = app_client.get(url, headers=headers)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))  # multi array with csv format
    assert array_response == ['A', 'B', 'C', 'D', 'E', 'F']
    url = '/v1.0/test_array_pipes_query_param?items=4&items=5&items=6&items=7|8|9'
    response = app_client.get(url, headers=headers)
    array_response: List[int] = json.loads(response.data.decode('utf-8', 'replace'))  # multi array with pipes format
    assert array_response == [7, 8, 9]


def test_array_form_param(simple_app):
    app_client = simple_app.app.test_client()
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    url = '/v1.0/test_array_csv_form_param'
    response = app_client.post(url, headers=headers)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))
    assert array_response == ['squash', 'banana']
    url = '/v1.0/test_array_csv_form_param'
    response = app_client.post(url, headers=headers, data={"items": "one,two,three"})
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))
    assert array_response == ['one', 'two', 'three']
    url = '/v1.0/test_array_pipes_form_param'
    response = app_client.post(url, headers=headers, data={"items": "1|2|3"})
    array_response: List[int] = json.loads(response.data.decode('utf-8', 'replace'))
    assert array_response == [1, 2, 3]
    url = '/v1.0/test_array_csv_form_param'
    data = 'items=A&items=B&items=C&items=D,E,F'
    response = app_client.post(url, headers=headers, data=data)
    array_response: List[str] = json.loads(response.data.decode('utf-8', 'replace'))  # multi array with csv format
    assert array_response == ['D', 'E', 'F']
    url = '/v1.0/test_array_pipes_form_param'
    data = 'items=4&items=5&items=6&items=7|8|9'
    response = app_client.post(url, headers=headers, data=data)
    array_response: List[int] = json.loads(response.data.decode('utf-8', 'replace'))  # multi array with pipes format
    assert array_response == [7, 8, 9]


def test_extra_query_param(simple_app):
    app_client = simple_app.app.test_client()
    headers = {'Content-type': 'application/json'}
    url = '/v1.0/test_parameter_validation?extra_parameter=true'
    resp = app_client.get(url, headers=headers)
    assert resp.status_code == 200


def test_strict_extra_query_param(strict_app):
    app_client = strict_app.app.test_client()
    headers = {'Content-type': 'application/json'}
    url = '/v1.0/test_parameter_validation?extra_parameter=true'
    resp = app_client.get(url, headers=headers)
    assert resp.status_code == 400
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response['detail'] == "Extra query parameter(s) extra_parameter not in spec"


def test_strict_formdata_param(strict_app):
    app_client = strict_app.app.test_client()
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    url = '/v1.0/test_array_csv_form_param'
    resp = app_client.post(url, headers=headers, data={"items":"mango"})
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response == ['mango']
    assert resp.status_code == 200


@pytest.mark.parametrize('arg, result', [
    # The cases accepted by the Flask/Werkzeug converter
    ['123', 'int 123'],
    ['0', 'int 0'],
    ['0000', 'int 0'],
    # Additional cases that we want to support
    ['+123', 'int 123'],
    ['+0', 'int 0'],
    ['-0', 'int 0'],
    ['-123', 'int -123'],
])
def test_path_parameter_someint(simple_app, arg, result):
    assert isinstance(arg, str)  # sanity check
    app_client = simple_app.app.test_client()
    resp = app_client.get(f'/v1.0/test-int-path/{arg}')  # type: flask.Response
    assert resp.data.decode('utf-8', 'replace') == f'"{result}"\n'


def test_path_parameter_someint__bad(simple_app):
    # non-integer values will not match Flask route
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-int-path/foo')  # type: flask.Response
    assert resp.status_code == 404


@pytest.mark.parametrize('arg, result', [
    # The cases accepted by the Flask/Werkzeug converter
    ['123.45', 'float 123.45'],
    ['123.0', 'float 123'],
    ['0.999999999999999999', 'float 1'],
    # Additional cases that we want to support
    ['+123.45', 'float 123.45'],
    ['-123.45', 'float -123.45'],
    ['123.', 'float 123'],
    ['.45', 'float 0.45'],
    ['123', 'float 123'],
    ['0', 'float 0'],
    ['0000', 'float 0'],
    ['-0.000000001', 'float -1e-09'],
    ['100000000000', 'float 1e+11'],
])
def test_path_parameter_somefloat(simple_app, arg, result):
    assert isinstance(arg, str)  # sanity check
    app_client = simple_app.app.test_client()
    resp = app_client.get(f'/v1.0/test-float-path/{arg}')  # type: flask.Response
    assert resp.data.decode('utf-8', 'replace') == f'"{result}"\n'


@pytest.mark.parametrize('arg, arg2, result', [
    ['-0.000000001', '0.3', 'float -1e-09, 0.3'],
])
def test_path_parameter_doublefloat(simple_app, arg, arg2, result):
    assert isinstance(arg, str)  # sanity check
    app_client = simple_app.app.test_client()
    resp = app_client.get(f'/v1.0/test-float-path/{arg}/{arg2}')  # type: flask.Response
    assert resp.data.decode('utf-8', 'replace') == f'"{result}"\n'


def test_path_parameter_somefloat__bad(simple_app):
    # non-float values will not match Flask route
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-float-path/123,45')  # type: flask.Response
    assert resp.status_code == 404


def test_default_param(strict_app):
    app_client = strict_app.app.test_client()
    resp = app_client.get('/v1.0/test-default-query-parameter')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response['app_name'] == 'connexion'


def test_falsy_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-falsy-param', query_string={'falsy': 0})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response == 0

    resp = app_client.get('/v1.0/test-falsy-param')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response == 1


def test_formdata_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param',
                           data={'formData': 'test'})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response == 'test'


def test_formdata_bad_request(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param')
    assert resp.status_code == 400
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response['detail'] in [
        "Missing formdata parameter 'formData'",
        "'formData' is a required property" # OAS3
    ]


def test_formdata_missing_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-missing-param',
                           data={'missing_formData': 'test'})
    assert resp.status_code == 200


def test_formdata_extra_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param',
                           data={'formData': 'test',
                                 'extra_formData': 'test'})
    assert resp.status_code == 200


def test_strict_formdata_extra_param(strict_app):
    app_client = strict_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param',
                           data={'formData': 'test',
                                 'extra_formData': 'test'})
    assert resp.status_code == 400
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response['detail'] == "Extra formData parameter(s) extra_formData not in spec"


def test_formdata_file_upload(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-file-upload',
                           data={'formData': (BytesIO(b'file contents'), 'filename.txt')})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response == {'filename.txt': 'file contents'}


def test_formdata_file_upload_bad_request(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-file-upload')
    assert resp.status_code == 400
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response['detail'] in [
        "Missing formdata parameter 'formData'",
        "'formData' is a required property" # OAS3
    ]


def test_formdata_file_upload_missing_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-file-upload-missing-param',
                           data={'missing_formData': (BytesIO(b'file contents'), 'example.txt')})
    assert resp.status_code == 200


def test_body_not_allowed_additional_properties(simple_app):
    app_client = simple_app.app.test_client()
    body = { 'body1': 'bodyString', 'additional_property': 'test1'}
    resp = app_client.post(
        '/v1.0/body-not-allowed-additional-properties',
        data=json.dumps(body),
        headers={'Content-Type': 'application/json'})
    assert resp.status_code == 400

    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert 'Additional properties are not allowed' in response['detail']

def test_bool_as_default_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-param')
    assert resp.status_code == 200

    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': True})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response is True


def test_bool_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': True})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response is True

    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': False})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response is False


def test_bool_array_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param?thruthiness=true,true,true')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response is True

    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param?thruthiness=true,true,false')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode('utf-8', 'replace'))
    assert response is False

    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param')
    assert resp.status_code == 200


def test_required_param_miss_config(simple_app):
    app_client = simple_app.app.test_client()

    resp = app_client.get('/v1.0/test-required-param')
    assert resp.status_code == 400

    resp = app_client.get('/v1.0/test-required-param', query_string={'simple': 'test'})
    assert resp.status_code == 200

    resp = app_client.get('/v1.0/test-required-param')
    assert resp.status_code == 400


def test_parameters_defined_in_path_level(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/parameters-in-root-path?title=nice-get')
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == ["nice-get"]

    resp = app_client.get('/v1.0/parameters-in-root-path')
    assert resp.status_code == 400


def test_array_in_path(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-array-in-path/one_item')
    assert json.loads(resp.data.decode('utf-8', 'replace')) == ["one_item"]

    resp = app_client.get('/v1.0/test-array-in-path/one_item,another_item')
    assert json.loads(resp.data.decode('utf-8', 'replace')) == ["one_item", "another_item"]


def test_nullable_parameter(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/nullable-parameters?time_start=null')
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'it was None'

    resp = app_client.get('/v1.0/nullable-parameters?time_start=None')
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'it was None'

    time_start = 1010
    resp = app_client.get(
        f'/v1.0/nullable-parameters?time_start={time_start}')
    assert json.loads(resp.data.decode('utf-8', 'replace')) == time_start

    resp = app_client.post('/v1.0/nullable-parameters', data={"post_param": 'None'})
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'it was None'

    resp = app_client.post('/v1.0/nullable-parameters', data={"post_param": 'null'})
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'it was None'

    headers = {"Content-Type": "application/json"}
    resp = app_client.put('/v1.0/nullable-parameters', data="null", headers=headers)
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'it was None'

    resp = app_client.put('/v1.0/nullable-parameters', data="None", headers=headers)
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'it was None'

    resp = app_client.put('/v1.0/nullable-parameters-noargs', data="None", headers=headers)
    assert json.loads(resp.data.decode('utf-8', 'replace')) == 'hello'


def test_args_kwargs(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/query-params-as-kwargs')
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == {}

    resp = app_client.get('/v1.0/query-params-as-kwargs?foo=a&bar=b')
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == {'foo': 'a'}

    if simple_app._spec_file == 'openapi.yaml':
        body = { 'foo': 'a', 'bar': 'b' }
        resp = app_client.post(
            '/v1.0/body-params-as-kwargs',
            data=json.dumps(body),
            headers={'Content-Type': 'application/json'})
        assert resp.status_code == 200
        # having only kwargs, the handler would have been passed 'body'
        assert json.loads(resp.data.decode('utf-8', 'replace')) == {'body': {'foo': 'a', 'bar': 'b'}, }


def test_param_sanitization(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/param-sanitization')
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == {}

    resp = app_client.post('/v1.0/param-sanitization?$query=queryString',
            data={'$form': 'formString'})
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == {
            'query': 'queryString',
            'form': 'formString',
            }

    body = { 'body1': 'bodyString', 'body2': 'otherString' }
    resp = app_client.post(
        '/v1.0/body-sanitization',
        data=json.dumps(body),
        headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == body

    body = { 'body1': 'bodyString', 'body2': 12, 'body3': {'a':'otherString' }}
    resp = app_client.post(
        '/v1.0/body-sanitization-additional-properties',
        data=json.dumps(body),
        headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == body

    body = {'body1': 'bodyString', 'additional_property': 'test1', 'additional_property2': 'test2'}
    resp = app_client.post(
        '/v1.0/body-sanitization-additional-properties-defined',
        data=json.dumps(body),
        headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8', 'replace')) == body

def test_no_sanitization_in_request_body(simple_app):
    app_client = simple_app.app.test_client()
    data = {
        'name': 'John',
        '$surname': 'Doe',
        '1337': True,
        '!#/bin/sh': False,
        '(1/0)': 'division by zero',
        's/$/EOL/': 'regular expression',
        '@8am': 'time',
    }
    response = app_client.post('/v1.0/forward', json=data)

    assert response.status_code == 200
    assert response.json == data

def test_parameters_snake_case(snake_case_app):
    app_client = snake_case_app.app.test_client()
    headers = {'Content-type': 'application/json'}
    resp = app_client.post('/v1.0/test-post-path-snake/123', headers=headers, data=json.dumps({"a": "test"}))
    assert resp.status_code == 200
    resp = app_client.post('/v1.0/test-post-path-shadow/123', headers=headers, data=json.dumps({"a": "test"}))
    assert resp.status_code == 200
    resp = app_client.post('/v1.0/test-post-query-snake?someId=123', headers=headers, data=json.dumps({"a": "test"}))
    assert resp.status_code == 200
    resp = app_client.post('/v1.0/test-post-query-shadow?id=123&class=header', headers=headers, data=json.dumps({"a": "test"}))
    assert resp.status_code == 200
    resp = app_client.get('/v1.0/test-get-path-snake/123')
    assert resp.status_code == 200
    resp = app_client.get('/v1.0/test-get-path-shadow/123')
    assert resp.status_code == 200
    resp = app_client.get('/v1.0/test-get-query-snake?someId=123')
    assert resp.status_code == 200
    resp = app_client.get('/v1.0/test-get-query-shadow?list=123')
    assert resp.status_code == 200
    # Tests for when CamelCase parameter is supplied, of which the snake_case version
    # matches an existing parameter and view func argument, or vice versa
    resp = app_client.get('/v1.0/test-get-camel-case-version?truthiness=true&orderBy=asc')
    assert resp.status_code == 200
    assert resp.get_json() == {'truthiness': True, 'order_by': 'asc'}
    resp = app_client.get('/v1.0/test-get-camel-case-version?truthiness=5')
    assert resp.status_code == 400
    assert resp.get_json()['detail'] == "Wrong type, expected 'boolean' for query parameter 'truthiness'"
    # Incorrectly cased params should be ignored
    resp = app_client.get('/v1.0/test-get-camel-case-version?Truthiness=true&order_by=asc')
    assert resp.status_code == 200
    assert resp.get_json() == {'truthiness': False, 'order_by': None}  # default values
    resp = app_client.get('/v1.0/test-get-camel-case-version?Truthiness=5&order_by=4')
    assert resp.status_code == 200
    assert resp.get_json() == {'truthiness': False, 'order_by': None}  # default values
    # TODO: Add tests for body parameters


def test_get_unicode_request(simple_app):
    """Regression test for Python 2 UnicodeEncodeError bug during parameter parsing."""
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/get_unicode_request?price=%C2%A319.99')  # £19.99
    assert resp.status_code == 200
    assert json.loads(resp.data.decode('utf-8'))['price'] == '£19.99'


def test_cookie_param(simple_app):
    app_client = simple_app.app.test_client()
    app_client.set_cookie(domain="localhost", key="test_cookie", value="hello")
    response = app_client.get("/v1.0/test-cookie-param")
    assert response.status_code == 200
    assert response.json == {"cookie_value": "hello"}
