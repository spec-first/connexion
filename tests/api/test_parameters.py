import json
from io import BytesIO


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


def test_path_parameter_someint(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-int-path/123')  # type: flask.Response
    assert resp.data.decode() == '"int"'

    # non-integer values will not match Flask route
    resp = app_client.get('/v1.0/test-int-path/foo')  # type: flask.Response
    assert resp.status_code == 404


def test_path_parameter_somefloat(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-float-path/123.45')  # type: flask.Response
    assert resp.data.decode() == '"float"'

    # non-float values will not match Flask route
    resp = app_client.get('/v1.0/test-float-path/123,45')  # type: flask.Response
    assert resp.status_code == 404


def test_default_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-default-query-parameter')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response['app_name'] == 'connexion'


def test_falsy_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-falsy-param', query_string={'falsy': 0})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 0

    resp = app_client.get('/v1.0/test-falsy-param')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 1


def test_formdata_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param',
                           data={'formData': 'test'})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == 'test'


def test_formdata_bad_request(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-param')
    assert resp.status_code == 400
    response = json.loads(resp.data.decode())
    assert response['detail'] == "Missing formdata parameter 'formData'"


def test_formdata_missing_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-missing-param',
                           data={'missing_formData': 'test'})
    assert resp.status_code == 200


def test_formdata_file_upload(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-file-upload',
                           data={'formData': (BytesIO(b'file contents'), 'filename.txt')})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response == {'filename.txt': 'file contents'}


def test_formdata_file_upload_bad_request(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-file-upload')
    assert resp.status_code == 400
    response = json.loads(resp.data.decode())
    assert response['detail'] == "Missing formdata parameter 'formData'"


def test_formdata_file_upload_missing_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.post('/v1.0/test-formData-file-upload-missing-param',
                           data={'missing_formData': (BytesIO(b'file contents'), 'example.txt')})
    assert resp.status_code == 200


def test_bool_as_default_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-param')
    assert resp.status_code == 200

    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': True})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is True


def test_bool_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': True})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is True

    resp = app_client.get('/v1.0/test-bool-param', query_string={'thruthiness': False})
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is False


def test_bool_array_param(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param?thruthiness=true,true,true')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
    assert response is True

    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-bool-array-param?thruthiness=true,true,false')
    assert resp.status_code == 200
    response = json.loads(resp.data.decode())
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
    assert json.loads(resp.data.decode()) == ["nice-get"]

    resp = app_client.get('/v1.0/parameters-in-root-path')
    assert resp.status_code == 400


def test_array_in_path(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-array-in-path/one_item')
    assert json.loads(resp.data.decode()) == ["one_item"]

    resp = app_client.get('/v1.0/test-array-in-path/one_item,another_item')
    assert json.loads(resp.data.decode()) == ["one_item", "another_item"]


def test_nullable_parameter(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/nullable-parameters?time_start=null')
    assert json.loads(resp.data.decode()) == 'it was None'

    resp = app_client.get('/v1.0/nullable-parameters?time_start=None')
    assert json.loads(resp.data.decode()) == 'it was None'

    time_start = 1010
    resp = app_client.get(
        '/v1.0/nullable-parameters?time_start={}'.format(time_start))
    assert json.loads(resp.data.decode()) == time_start

    resp = app_client.post('/v1.0/nullable-parameters', data={"post_param": 'None'})
    assert json.loads(resp.data.decode()) == 'it was None'

    resp = app_client.post('/v1.0/nullable-parameters', data={"post_param": 'null'})
    assert json.loads(resp.data.decode()) == 'it was None'

    resp = app_client.put('/v1.0/nullable-parameters', data="null")
    assert json.loads(resp.data.decode()) == 'it was None'

    resp = app_client.put('/v1.0/nullable-parameters', data="None")
    assert json.loads(resp.data.decode()) == 'it was None'
