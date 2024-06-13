import abc
import collections.abc
import functools
import logging
import types
import typing as t
from enum import Enum

from connexion import utils
from connexion.context import operation
from connexion.datastructures import NoContent
from connexion.exceptions import NonConformingResponseHeaders
from connexion.frameworks.abstract import Framework
from connexion.lifecycle import ConnexionResponse

logger = logging.getLogger(__name__)


class BaseResponseDecorator:
    def __init__(self, *, framework: t.Type[Framework], jsonifier):
        self.framework = framework
        self.jsonifier = jsonifier

    @abc.abstractmethod
    def __call__(self, function: t.Callable) -> t.Callable:
        raise NotImplementedError

    def build_framework_response(self, handler_response):
        data, status_code, headers = self._unpack_handler_response(handler_response)
        content_type = self._infer_content_type(data, headers)
        if not self.framework.is_framework_response(data):
            data = self._serialize_data(data, content_type=content_type)
            status_code = status_code or self._infer_status_code(data)
            headers = self._update_headers(headers, content_type=content_type)
        return self.framework.build_response(
            data, content_type=content_type, status_code=status_code, headers=headers
        )

    @staticmethod
    def _infer_content_type(data: t.Any, headers: dict) -> t.Optional[str]:
        """Infer the response content type from the returned data, headers and operation spec.

        :param data: Response data
        :param headers: Headers returned by the handler.

        :return: Inferred content type

        :raises: NonConformingResponseHeaders if content type cannot be deducted.
        """
        content_type = utils.extract_content_type(headers)

        # TODO: don't default
        produces = list(set(operation.produces))
        if data is not None and not produces:
            produces = ["application/json"]

        if content_type:
            if content_type not in produces:
                raise NonConformingResponseHeaders(
                    f"Returned content type ({content_type}) is not defined in operation spec "
                    f"({operation.produces})."
                )
        else:
            if not produces:
                # Produces can be empty/ for empty responses
                pass
            elif len(produces) == 1:
                content_type = produces[0]
            else:
                if isinstance(data, str):
                    for produced_content_type in produces:
                        if "text/plain" in produced_content_type:
                            content_type = produced_content_type
                elif isinstance(data, bytes) or isinstance(
                    data, (types.GeneratorType, collections.abc.Iterator)
                ):
                    for produced_content_type in produces:
                        if "application/octet-stream" in produced_content_type:
                            content_type = produced_content_type

                if content_type is None:
                    raise NonConformingResponseHeaders(
                        "Multiple response content types are defined in the operation spec, but "
                        "the handler response did not specify which one to return."
                    )

        return content_type

    def _serialize_data(self, data: t.Any, *, content_type: str) -> t.Any:
        """Serialize the data based on the content type."""
        if data is None or data is NoContent:
            return None
        # TODO: encode responses
        mime_type, _ = utils.split_content_type(content_type)
        if utils.is_json_mimetype(mime_type):
            return self.jsonifier.dumps(data)
        return data

    @staticmethod
    def _infer_status_code(data: t.Any) -> int:
        """Infer the status code from the returned data."""
        if data is None:
            return 204
        return 200

    @staticmethod
    def _update_headers(
        headers: t.Dict[str, str], *, content_type: str
    ) -> t.Dict[str, str]:
        # Check if Content-Type is in headers, taking into account case-insensitivity
        for key, value in headers.items():
            if key.lower() == "content-type":
                return headers

        if content_type:
            headers["Content-Type"] = content_type
        return headers

    @staticmethod
    def _unpack_handler_response(
        handler_response: t.Union[str, bytes, dict, list, tuple]
    ) -> t.Tuple[t.Union[str, bytes, dict, list, None], t.Optional[int], dict]:
        """Unpack the handler response into data, status_code and headers.

        :param handler_response: The response returned from the handler function if it was not a
            response class.

        :return: A tuple of data, status_code and headers
        """
        data, status_code, headers = None, None, {}

        if not isinstance(handler_response, tuple):
            data = handler_response

        elif len(handler_response) == 1:
            (data,) = handler_response

        elif len(handler_response) == 2:
            data, status_code_or_headers = handler_response
            if isinstance(status_code_or_headers, int):
                # Extra int call because of int subclasses such as http.HTTPStatus (IntEnum)
                status_code = int(status_code_or_headers)
            elif isinstance(status_code_or_headers, Enum) and isinstance(
                status_code_or_headers.value, int
            ):
                status_code = status_code_or_headers.value
            else:
                headers = status_code_or_headers

        elif len(handler_response) == 3:
            data, status_code, headers = handler_response

        else:
            raise TypeError(
                "The view function did not return a valid response tuple."
                " The tuple must have the form (body), (body, status, headers),"
                " (body, status), or (body, headers)."
            )

        return data, status_code, headers


class SyncResponseDecorator(BaseResponseDecorator):
    def __call__(self, function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            """
            This method converts a handler response to a framework response.
            The handler response can be a ConnexionResponse, a framework response, a tuple or an
            object.
            """
            handler_response = function(*args, **kwargs)
            if self.framework.is_framework_response(handler_response):
                return handler_response
            elif isinstance(handler_response, ConnexionResponse):
                return self.framework.connexion_to_framework_response(handler_response)
            else:
                return self.build_framework_response(handler_response)

        return wrapper


class AsyncResponseDecorator(BaseResponseDecorator):
    def __call__(self, function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            """
            This method converts a handler response to a framework response.
            The handler response can be a ConnexionResponse, a framework response, a tuple or an
            object.
            """
            handler_response = await function(*args, **kwargs)
            if self.framework.is_framework_response(handler_response):
                return handler_response
            elif isinstance(handler_response, ConnexionResponse):
                return self.framework.connexion_to_framework_response(handler_response)
            else:
                return self.build_framework_response(handler_response)

        return wrapper


class NoResponseDecorator(BaseResponseDecorator):
    """Dummy decorator to skip response serialization."""

    def __call__(self, function: t.Callable) -> t.Callable:
        return lambda request: function(request)
