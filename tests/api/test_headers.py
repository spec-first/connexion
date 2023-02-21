import json


def test_headers_jsonifier(simple_app):
    app_client = simple_app.test_client()

    response = app_client.post("/v1.0/goodday/dan", data={})
    assert response.status_code == 201
    # Default Werkzeug behavior was changed in 2.1 (https://github.com/pallets/werkzeug/issues/2352)
    assert response.headers["Location"] in ["http://localhost/my/uri", "/my/uri"]


def test_headers_produces(simple_app):
    app_client = simple_app.test_client()

    response = app_client.post("/v1.0/goodevening/dan", data={})
    assert response.status_code == 201
    # Default Werkzeug behavior was changed in 2.1 (https://github.com/pallets/werkzeug/issues/2352)
    assert response.headers["Location"] in ["http://localhost/my/uri", "/my/uri"]


def test_header_not_returned(simple_openapi_app):
    app_client = simple_openapi_app.test_client()

    response = app_client.post("/v1.0/goodday/noheader", data={})
    assert (
        response.status_code == 500
    )  # view_func has not returned what was promised in spec
    assert response.headers.get("content-type") == "application/problem+json"
    data = response.json()
    assert data["type"] == "about:blank"
    assert data["title"] == "Internal Server Error"
    assert (
        data["detail"]
        == "Keys in response header don't match response specification. Difference: location"
    )
    assert data["status"] == 500


def test_no_content_response_have_headers(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-204-with-headers")
    assert resp.status_code == 204
    assert "X-Something" in resp.headers


def test_no_content_object_and_have_headers(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-204-with-headers-nocontent-obj")
    assert resp.status_code == 204
    assert "X-Something" in resp.headers


def test_optional_header(simple_openapi_app):
    app_client = simple_openapi_app.test_client()
    resp = app_client.get("/v1.0/test-optional-headers")
    assert resp.status_code == 200
    assert "X-Optional-Header" not in resp.headers
