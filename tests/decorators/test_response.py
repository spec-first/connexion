import collections.abc
from enum import Enum
from unittest.mock import MagicMock, patch

import connexion.decorators.response
import pytest
from connexion.datastructures import NoContent
from connexion.decorators.response import (
    AsyncResponseDecorator,
    BaseResponseDecorator,
    NoResponseDecorator,
    SyncResponseDecorator,
)
from connexion.exceptions import NonConformingResponseHeaders
from connexion.lifecycle import ConnexionResponse
from connexion.utils import extract_content_type, is_json_mimetype, split_content_type


@pytest.fixture
def mock_framework():
    """Create a mock Framework class."""
    framework = MagicMock()
    framework.is_framework_response.return_value = False
    framework.build_response.return_value = "framework_response"
    framework.connexion_to_framework_response.return_value = (
        "connexion_to_framework_response"
    )
    return framework


@pytest.fixture
def mock_jsonifier():
    """Create a mock jsonifier object."""
    jsonifier = MagicMock()
    jsonifier.dumps.side_effect = lambda x: f"json:{x}"
    return jsonifier


@pytest.fixture(autouse=True)
def patch_operation_context(monkeypatch):
    # Create a mock operation object
    mock_operation = MagicMock()
    mock_operation.produces = ["application/json"]

    monkeypatch.setattr(connexion.decorators.response, "operation", mock_operation)

    original_extract_content_type = extract_content_type
    original_split_content_type = split_content_type
    original_is_json_mimetype = is_json_mimetype

    monkeypatch.setattr(
        connexion.decorators.response.utils,
        "extract_content_type",
        original_extract_content_type,
    )
    monkeypatch.setattr(
        connexion.decorators.response.utils,
        "split_content_type",
        original_split_content_type,
    )
    monkeypatch.setattr(
        connexion.decorators.response.utils,
        "is_json_mimetype",
        original_is_json_mimetype,
    )

    return mock_operation


class TestBaseResponseDecorator:
    """Test the BaseResponseDecorator class."""

    def test_abstract_class(self):
        """Test that BaseResponseDecorator is abstract."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        with pytest.raises(NotImplementedError):
            decorator(lambda: None)

    def test_unpack_handler_response_simple(self):
        """Test _unpack_handler_response with a simple value."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        data, status_code, headers = decorator._unpack_handler_response("test_data")
        assert data == "test_data"
        assert status_code is None
        assert headers == {}

    def test_unpack_handler_response_tuple_1(self):
        """Test _unpack_handler_response with a 1-tuple."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        data, status_code, headers = decorator._unpack_handler_response(("test_data",))
        assert data == "test_data"
        assert status_code is None
        assert headers == {}

    def test_unpack_handler_response_tuple_2_status(self):
        """Test _unpack_handler_response with a 2-tuple containing status code."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        data, status_code, headers = decorator._unpack_handler_response(
            ("test_data", 201)
        )
        assert data == "test_data"
        assert status_code == 201
        assert headers == {}

    def test_unpack_handler_response_tuple_2_headers(self):
        """Test _unpack_handler_response with a 2-tuple containing headers."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        headers_dict = {"Content-Type": "text/plain"}
        data, status_code, headers = decorator._unpack_handler_response(
            ("test_data", headers_dict)
        )
        assert data == "test_data"
        assert status_code is None
        assert headers == headers_dict

    def test_unpack_handler_response_tuple_3(self):
        """Test _unpack_handler_response with a 3-tuple."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        headers_dict = {"Content-Type": "text/plain"}
        data, status_code, headers = decorator._unpack_handler_response(
            ("test_data", 201, headers_dict)
        )
        assert data == "test_data"
        assert status_code == 201
        assert headers == headers_dict

    def test_unpack_handler_response_tuple_too_long(self):
        """Test _unpack_handler_response with too many tuple items."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        with pytest.raises(TypeError):
            decorator._unpack_handler_response(("test_data", 201, {}, "extra"))

    def test_unpack_handler_response_enum_status(self):
        """Test _unpack_handler_response with an enum status code."""

        class HttpStatus(Enum):
            CREATED = 201

        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        data, status_code, headers = decorator._unpack_handler_response(
            ("test_data", HttpStatus.CREATED)
        )
        assert data == "test_data"
        assert status_code == 201
        assert headers == {}

    def test_infer_status_code_with_data(self):
        """Test _infer_status_code with data."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        assert decorator._infer_status_code("test_data") == 200

    def test_infer_status_code_without_data(self):
        """Test _infer_status_code without data."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        assert decorator._infer_status_code(None) == 204

    def test_update_headers_with_content_type(self):
        """Test _update_headers with content type."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        headers = decorator._update_headers({}, content_type="application/json")
        assert headers == {"Content-Type": "application/json"}

    def test_update_headers_with_existing_content_type(self):
        """Test _update_headers with existing content type header."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        headers = decorator._update_headers(
            {"Content-Type": "text/plain"}, content_type="application/json"
        )
        assert headers == {"Content-Type": "text/plain"}

    def test_update_headers_case_insensitive(self):
        """Test _update_headers with case-insensitive content type header."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        headers = decorator._update_headers(
            {"content-type": "text/plain"}, content_type="application/json"
        )
        assert headers == {"content-type": "text/plain"}

    def test_serialize_data_json(self, mock_jsonifier):
        """Test _serialize_data with JSON content type."""
        decorator = BaseResponseDecorator(
            framework=MagicMock(), jsonifier=mock_jsonifier
        )
        result = decorator._serialize_data("test_data", content_type="application/json")
        assert result == "json:test_data"
        mock_jsonifier.dumps.assert_called_once_with("test_data")

    def test_serialize_data_text(self, mock_jsonifier):
        """Test _serialize_data with text content type."""
        decorator = BaseResponseDecorator(
            framework=MagicMock(), jsonifier=mock_jsonifier
        )
        result = decorator._serialize_data("test_data", content_type="text/plain")
        assert result == "test_data"
        mock_jsonifier.dumps.assert_not_called()

    def test_serialize_data_none(self, mock_jsonifier):
        """Test _serialize_data with None data."""
        decorator = BaseResponseDecorator(
            framework=MagicMock(), jsonifier=mock_jsonifier
        )
        assert decorator._serialize_data(None, content_type="application/json") is None
        assert (
            decorator._serialize_data(NoContent, content_type="application/json")
            is None
        )

    def test_infer_content_type_from_headers(self, patch_operation_context):
        """Test _infer_content_type from headers."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        content_type = decorator._infer_content_type(
            "test_data", {"Content-Type": "application/json"}
        )
        assert content_type == "application/json"

    def test_infer_content_type_from_headers_non_conforming(
        self, patch_operation_context
    ):
        """Test _infer_content_type with non-conforming headers."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        with pytest.raises(NonConformingResponseHeaders):
            decorator._infer_content_type("test_data", {"Content-Type": "text/plain"})

    def test_infer_content_type_single_produces(self, patch_operation_context):
        """Test _infer_content_type with single produces value."""
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        content_type = decorator._infer_content_type("test_data", {})
        assert content_type == "application/json"

    def test_infer_content_type_multiple_produces_text(self, patch_operation_context):
        """Test _infer_content_type with multiple produces values and text data."""
        patch_operation_context.produces = ["application/json", "text/plain"]
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        content_type = decorator._infer_content_type("test_data", {})
        assert content_type == "text/plain"

    def test_infer_content_type_multiple_produces_bytes(self, patch_operation_context):
        """Test _infer_content_type with multiple produces values and bytes data."""
        patch_operation_context.produces = [
            "application/json",
            "application/octet-stream",
        ]
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        content_type = decorator._infer_content_type(b"test_data", {})
        assert content_type == "application/octet-stream"

    def test_infer_content_type_multiple_produces_generator(
        self, patch_operation_context
    ):
        """Test _infer_content_type with multiple produces values and generator data."""
        patch_operation_context.produces = [
            "application/json",
            "application/octet-stream",
        ]
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())

        def gen():
            yield b"test_data"

        content_type = decorator._infer_content_type(gen(), {})
        assert content_type == "application/octet-stream"

    def test_infer_content_type_multiple_produces_iterator(
        self, patch_operation_context
    ):
        """Test _infer_content_type with multiple produces values and iterator data."""
        patch_operation_context.produces = [
            "application/json",
            "application/octet-stream",
        ]
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())

        class TestIterator(collections.abc.Iterator):
            def __next__(self):
                return b"test_data"

        content_type = decorator._infer_content_type(TestIterator(), {})
        assert content_type == "application/octet-stream"

    def test_infer_content_type_multiple_produces_error(self, patch_operation_context):
        """Test _infer_content_type with multiple produces values and no matching type."""
        patch_operation_context.produces = ["application/json", "application/xml"]
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        with pytest.raises(NonConformingResponseHeaders):
            decorator._infer_content_type({}, {})

    def test_infer_content_type_no_produces_with_data(self, patch_operation_context):
        """Test _infer_content_type with no produces and data."""
        patch_operation_context.produces = []
        decorator = BaseResponseDecorator(framework=MagicMock(), jsonifier=MagicMock())
        content_type = decorator._infer_content_type({}, {})
        assert content_type == "application/json"

    def test_build_framework_response(self, mock_framework, mock_jsonifier):
        """Test build_framework_response."""
        decorator = BaseResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )
        response = decorator.build_framework_response("test_data")
        assert response == "framework_response"
        mock_framework.build_response.assert_called_once_with(
            "json:test_data",
            content_type="application/json",
            status_code=200,
            headers={"Content-Type": "application/json"},
        )


class TestSyncResponseDecorator:
    """Test the SyncResponseDecorator class."""

    def test_call_simple_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a simple response."""
        decorator = SyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )

        def handler():
            return "test_data"

        wrapped = decorator(handler)
        response = wrapped()

        assert response == "framework_response"
        mock_framework.build_response.assert_called_once()

    def test_call_framework_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a framework response."""
        decorator = SyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )
        mock_framework.is_framework_response.return_value = True

        def handler():
            return "framework_response"

        wrapped = decorator(handler)
        response = wrapped()

        assert response == "framework_response"
        mock_framework.build_response.assert_not_called()

    def test_call_connexion_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a ConnexionResponse."""
        decorator = SyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )

        def handler():
            return ConnexionResponse(body="test_data")

        wrapped = decorator(handler)
        response = wrapped()

        assert response == "connexion_to_framework_response"
        mock_framework.connexion_to_framework_response.assert_called_once()


class TestAsyncResponseDecorator:
    """Test the AsyncResponseDecorator class."""

    @pytest.mark.asyncio
    async def test_call_simple_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a simple response."""
        decorator = AsyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )

        async def handler():
            return "test_data"

        wrapped = decorator(handler)
        response = await wrapped()

        assert response == "framework_response"
        mock_framework.build_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_framework_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a framework response."""
        decorator = AsyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )
        mock_framework.is_framework_response.return_value = True

        async def handler():
            return "framework_response"

        wrapped = decorator(handler)
        response = await wrapped()

        assert response == "framework_response"
        mock_framework.build_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_connexion_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a ConnexionResponse."""
        decorator = AsyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )

        async def handler():
            return ConnexionResponse(body="test_data")

        wrapped = decorator(handler)
        response = await wrapped()

        assert response == "connexion_to_framework_response"
        mock_framework.connexion_to_framework_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_coroutine_response(self, mock_framework, mock_jsonifier):
        """Test __call__ with a coroutine response."""
        decorator = AsyncResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )

        async def coro():
            return "test_data"

        async def handler():
            return coro()

        wrapped = decorator(handler)
        response = await wrapped()

        assert response == "framework_response"
        mock_framework.build_response.assert_called_once()


class TestNoResponseDecorator:
    """Test the NoResponseDecorator class."""

    def test_call(self, mock_framework, mock_jsonifier):
        """Test __call__ passes through the handler function."""
        decorator = NoResponseDecorator(
            framework=mock_framework, jsonifier=mock_jsonifier
        )

        def handler(request):
            return f"processed {request}"

        wrapped = decorator(handler)
        response = wrapped("test_request")

        assert response == "processed test_request"
