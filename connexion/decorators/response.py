import abc
import collections.abc
import functools
import logging
import types
import typing as t
from enum import Enum

from connexion.context import operation
from connexion.datastructures import NoContent
from connexion.exceptions import NonConformingResponseHeaders
from connexion.frameworks.abstract import Framework
from connexion.lifecycle import ConnexionResponse
from connexion.utils import is_json_mimetype

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
        content_type = self._deduct_content_type(data, headers)
        if not self.framework.is_framework_response(data):
            data, status_code = self._prepare_body_and_status_code(
                data, status_code=status_code, mimetype=content_type
            )
        return self.framework.build_response(
            data, content_type=content_type, status_code=status_code, headers=headers
        )

    @staticmethod
    def _deduct_content_type(data: t.Any, headers: dict) -> str:
        """Deduct the response content type from the returned data, headers and operation spec.

        :param data: Response data
        :param headers: Headers returned by the handler.

        :return: Deducted content type

        :raises: NonConformingResponseHeaders if content type cannot be deducted.
        """
        content_type = headers.get("Content-Type")

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
            elif isinstance(data, str) and "text/plain" in produces:
                content_type = "text/plain"
            elif (
                isinstance(data, bytes)
                or isinstance(data, (types.GeneratorType, collections.abc.Iterator))
            ) and "application/octet-stream" in produces:
                content_type = "application/octet-stream"
            else:
                raise NonConformingResponseHeaders(
                    "Multiple response content types are defined in the operation spec, but the "
                    "handler response did not specify which one to return."
                )

        return content_type

    def _prepare_body_and_status_code(
        self, data, *, status_code: int = None, mimetype: str
    ) -> tuple:
        if data is NoContent:
            data = None

        if status_code is None:
            if data is None:
                status_code = 204
            else:
                status_code = 200

        if data is not None:
            body = self._serialize_data(data, mimetype)
        else:
            body = data

        return body, status_code

    def _serialize_data(self, data: t.Any, mimetype: str) -> t.Any:
        if is_json_mimetype(mimetype):
            return self.jsonifier.dumps(data)
        return data

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
                status_code = status_code_or_headers
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
