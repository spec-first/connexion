from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

def test_cors_no_error(simple_app):
    app_client = simple_app.test_client()
    simple_app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    response = app_client.post("/v1.0/goodday/dan", data={})
    assert response.status_code == 201
    assert "Access-Control-Allow-Origin" in response.headers

def test_cors_validation_error(simple_openapi_app):
    app_client = simple_openapi_app.test_client()
    simple_openapi_app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    response = app_client.post("/v1.0/body-not-allowed-additional-properties", data={})
    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" in response.headers

def test_cors_server_error(simple_openapi_app):
    app_client = simple_openapi_app.test_client()
    simple_openapi_app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    assert "Access-Control-Allow-Origin" in response.headers
