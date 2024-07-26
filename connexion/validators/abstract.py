"""
This module defines a Validator interface with base functionality that can be subclassed
for custom validators provided to the RequestValidationMiddleware.
"""
import copy
import json
import typing as t

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import Receive, Scope, Send

from connexion.exceptions import BadRequestProblem


class AbstractRequestBodyValidator:
    """
    Validator interface with base functionality that can be subclassed for custom validators.

    .. note: Validators load the whole body into memory, which can be a problem for large payloads.
    """

    MUTABLE_VALIDATION = False
    """
    Whether mutations to the body during validation should be transmitted via the receive channel.
    Note that this does not apply to the substitution of a missing body with the default body, which always
    updates the receive channel.
    """
    MAX_MESSAGE_LENGTH = 256000
    """Maximum message length that will be sent via the receive channel for mutated bodies."""

    def __init__(
        self,
        *,
        schema: dict,
        required: bool = False,
        nullable: bool = False,
        encoding: str,
        strict_validation: bool,
        **kwargs,
    ):
        """
        :param schema: Schema of operation to validate
        :param required: Whether RequestBody is required
        :param nullable: Whether RequestBody is nullable
        :param encoding: Encoding of body (passed via Content-Type header)
        :param kwargs: Additional arguments for subclasses
        :param strict_validation: Whether to allow parameters not defined in the spec
        """
        self._schema = schema
        self._nullable = nullable
        self._required = required
        self._encoding = encoding
        self._strict_validation = strict_validation

    async def _parse(
        self, stream: t.AsyncGenerator[bytes, None], scope: Scope
    ) -> t.Any:
        """Parse the incoming stream."""

    def _validate(self, body: t.Any) -> t.Optional[dict]:
        """
        Validate the parsed body.

        :raises: :class:`connexion.exceptions.BadRequestProblem`
        """

    def _insert_body(
        self, receive: Receive, *, body: t.Any, scope: Scope
    ) -> t.Tuple[Receive, Scope]:
        """
        Insert messages transmitting the body at the start of the `receive` channel.

        This method updates the provided `scope` in place with the right `Content-Length` header.
        """
        if body is None:
            return receive, scope

        bytes_body = json.dumps(body).encode(self._encoding)

        # Update the content-length header
        new_scope = scope.copy()
        new_scope["headers"] = copy.deepcopy(scope["headers"])
        headers = MutableHeaders(scope=new_scope)
        headers["content-length"] = str(len(bytes_body))

        # Wrap in new receive channel
        messages = (
            {
                "type": "http.request",
                "body": bytes_body[i : i + self.MAX_MESSAGE_LENGTH],
                "more_body": i + self.MAX_MESSAGE_LENGTH < len(bytes_body),
            }
            for i in range(0, len(bytes_body), self.MAX_MESSAGE_LENGTH)
        )

        receive = self._insert_messages(receive, messages=messages)

        return receive, new_scope

    @staticmethod
    def _insert_messages(
        receive: Receive, *, messages: t.Iterable[t.MutableMapping[str, t.Any]]
    ) -> Receive:
        """Insert messages at the start of the `receive` channel."""
        # Ensure that messages is an iterator so each message is replayed once.
        message_iterator = iter(messages)

        async def receive_() -> t.MutableMapping[str, t.Any]:
            try:
                return next(message_iterator)
            except StopIteration:
                return await receive()

        return receive_

    async def wrap_receive(
        self, receive: Receive, *, scope: Scope
    ) -> t.Tuple[Receive, Scope]:
        """
        Wrap the provided `receive` channel with request body validation.

        This method updates the provided `scope` in place with the right `Content-Length` header.
        """
        # Handle missing bodies
        headers = Headers(scope=scope)
        if not int(headers.get("content-length", 0)):
            body = self._schema.get("default")
            if body is None and self._required:
                raise BadRequestProblem("RequestBody is required")
            # The default body is encoded as a `receive` channel to mimic an incoming body
            receive, scope = self._insert_body(receive, body=body, scope=scope)

        # The receive channel is converted to a stream for convenient access
        messages = []

        async def stream() -> t.AsyncGenerator[bytes, None]:
            more_body = True
            while more_body:
                message = await receive()
                messages.append(message)
                more_body = message.get("more_body", False)
                yield message.get("body", b"")
            yield b""

        # The body is parsed and validated
        body = await self._parse(stream(), scope=scope)
        if not (body is None and self._nullable):
            self._validate(body)

        # If MUTABLE_VALIDATION is enabled, include any changes made during validation in the messages to send
        if self.MUTABLE_VALIDATION:
            # Include changes made during validation
            receive, scope = self._insert_body(receive, body=body, scope=scope)
        else:
            # Serialize original messages
            receive = self._insert_messages(receive, messages=messages)

        return receive, scope


class AbstractResponseBodyValidator:
    """
    Validator interface with base functionality that can be subclassed for custom validators.

    .. note: Validators load the whole body into memory, which can be a problem for large payloads.
    """

    def __init__(
        self,
        scope: Scope,
        *,
        schema: dict,
        nullable: bool = False,
        encoding: str,
    ) -> None:
        self._scope = scope
        self._schema = schema
        self._nullable = nullable
        self._encoding = encoding

    def _parse(self, stream: t.Generator[bytes, None, None]) -> t.Any:
        """Parse the incoming stream."""

    def _validate(self, body: t.Any) -> t.Optional[dict]:
        """
        Validate the body.

        :raises: :class:`connexion.exceptions.NonConformingResponse`
        """

    def wrap_send(self, send: Send) -> Send:
        """Wrap the provided send channel with response body validation"""

        messages = []

        async def send_(message: t.MutableMapping[str, t.Any]) -> None:
            messages.append(message)

            if message["type"] == "http.response.start" or message.get(
                "more_body", False
            ):
                return

            stream = (message.get("body", b"") for message in messages)
            body = self._parse(stream)

            if not (body is None and self._nullable):
                self._validate(body)

            while messages:
                await send(messages.pop(0))

        return send_
