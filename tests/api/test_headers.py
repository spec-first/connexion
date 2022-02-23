import json


def test_headers_jsonifier(simple_app):
    app_client = simple_app.app.test_client()

    response = app_client.post('/v1.0/goodday/dan', data={})  # type: flask.Response
    assert response.status_code == 201
    assert response.headers["Location"] == "http://localhost/my/uri"


def test_headers_produces(simple_app):
    app_client = simple_app.app.test_client()

    response = app_client.post('/v1.0/goodevening/dan', data={})  # type: flask.Response
    assert response.status_code == 201
    assert response.headers["Location"] == "http://localhost/my/uri"


def test_header_not_returned(simple_openapi_app):
    app_client = simple_openapi_app.app.test_client()

    response = app_client.post('/v1.0/goodday/noheader', data={})  # type: flask.Response
    assert response.status_code == 500  # view_func has not returned what was promised in spec
    assert response.content_type == 'application/problem+json'
    data = json.loads(response.data.decode('utf-8', 'replace'))
    assert data['type'] == 'about:blank'
    assert data['title'] == 'Response headers do not conform to specification'
    assert data['detail'] == "Keys in header don't match response specification. Difference: Location"
    assert data['status'] == 500


def test_no_content_response_have_headers(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-204-with-headers')
    assert resp.status_code == 204
    assert 'X-Something' in resp.headers


def test_no_content_object_and_have_headers(simple_app):
    app_client = simple_app.app.test_client()
    resp = app_client.get('/v1.0/test-204-with-headers-nocontent-obj')
    assert resp.status_code == 204
    assert 'X-Something' in resp.headers


def test_optional_header(simple_openapi_app):
    app_client = simple_openapi_app.app.test_client()
    resp = app_client.get('/v1.0/test-optional-headers')
    assert resp.status_code == 200
    assert 'X-Optional-Header' not in resp.headers
