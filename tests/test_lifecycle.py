import json

import six

import pytest
from connexion.lifecycle import ConnexionResponse


class TestConnexionResponse(object):

    @pytest.mark.parametrize("status", [
        200,
        302,
        403,
        -1,
        "test",
        False,
        506
    ])
    @pytest.mark.xfail(raises=ValueError)
    def test_status_code(self, status):
        response = ConnexionResponse(status)
        assert response.status_code == status

    @pytest.mark.parametrize("body", [
        b"test",
        u"test",
    ])
    def test_text_and_data(self, body):
        response = ConnexionResponse(body=body)
        assert isinstance(response.text, six.text_type)
        assert isinstance(response.data, six.binary_type)

    @pytest.mark.parametrize("body", [
        '{"test": true}'
    ])
    def test_json(self, body):
        assert ConnexionResponse(body=body).json == json.loads(body)

    @pytest.mark.parametrize("body,expected", [
        ("test", 4),
        ("", 0),
        # Always count body as bytes, some unicode characters representation
        # is composed of multiple bytes
        ("€", 3)
    ])
    def test_content_length(self, body, expected):
        assert ConnexionResponse(body=body).content_length == expected
        response_with_headers = ConnexionResponse(
            body=body,
            headers={"Content-Length": str(len(body.encode("UTF-8")))},
        )
        assert response_with_headers.content_length == expected
