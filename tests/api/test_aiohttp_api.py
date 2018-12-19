import pytest

from aiohttp.web import Response, StreamResponse
from connexion.apis.aiohttp_api import AioHttpApi
from connexion.lifecycle import ConnexionResponse


@pytest.mark.parametrize("handler_response", [
    Response(),
    (Response(), ),
    StreamResponse()
])
def test__response_from_handler_aiohttp_response(handler_response):
    response = AioHttpApi._response_from_handler(handler_response)
    assert isinstance(response, StreamResponse)


@pytest.mark.parametrize("body", [
    "test",
    b"test"
])
def test__response_from_handler_tuple_1(body):
    response = AioHttpApi._response_from_handler((body, ))
    assert isinstance(response, Response)
    assert response.body == b"test"
    assert response.status == 200


@pytest.mark.parametrize("response_handler", [
    (("test", 200)),
    (("test", 404))
])
def test__response_from_handler_tuple_2(response_handler):
    response = AioHttpApi._response_from_handler(response_handler)
    assert isinstance(response, Response)
    assert response.body == b"test"
    assert response.status == response_handler[1]


@pytest.mark.parametrize("response_handler", [
    (("test", 404, {"x-test": "true"}))
])
def test__response_from_handler_tuple_3(response_handler):
    response = AioHttpApi._response_from_handler(response_handler)
    assert isinstance(response, Response)
    assert response.body == b"test"
    assert response.headers.get("x-test") == "true"


@pytest.mark.parametrize("response", [
    Response(),
    (("test",)),
    (("test", 200)),
    (("test", 200, {"Location": "http://test.com"})),
    ConnexionResponse()
])
def test_get_connexion_response(response):
    assert isinstance(
        AioHttpApi.get_connexion_response(response),
        ConnexionResponse
    )
