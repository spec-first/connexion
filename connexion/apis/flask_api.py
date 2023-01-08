"""
This module defines a Flask Connexion API which implements translations between Flask and
Connexion requests / responses.
"""
import logging
import typing as t

import flask
from flask import Response as FlaskResponse

from connexion.apis.abstract import AbstractAPI
from connexion.decorators import FlaskDecorator
from connexion.frameworks import flask as flask_utils
from connexion.jsonifier import Jsonifier
from connexion.operations import AbstractOperation
from connexion.uri_parsing import AbstractURIParser

logger = logging.getLogger("connexion.apis.flask_api")


class FlaskApi(AbstractAPI):

    jsonifier = Jsonifier(flask.json, indent=2)

    def _set_base_path(self, base_path):
        super()._set_base_path(base_path)
        self._set_blueprint()

    def _set_blueprint(self):
        logger.debug("Creating API blueprint: %s", self.base_path)
        endpoint = flask_utils.flaskify_endpoint(self.base_path)
        self.blueprint = flask.Blueprint(
            endpoint,
            __name__,
            url_prefix=self.base_path,
            template_folder=str(self.options.openapi_console_ui_from_dir),
        )

    def _add_operation_internal(self, method, path, operation):
        operation_id = operation.operation_id
        logger.debug(
            "... Adding %s -> %s", method.upper(), operation_id, extra=vars(operation)
        )

        flask_path = flask_utils.flaskify_path(
            path, operation.get_path_parameter_types()
        )
        endpoint_name = flask_utils.flaskify_endpoint(
            operation.operation_id, operation.randomize_endpoint
        )

        endpoint = FlaskOperation.from_operation(
            operation, pythonic_params=self.pythonic_params
        )

        self.blueprint.add_url_rule(
            flask_path, endpoint_name, endpoint, methods=[method]
        )


class FlaskOperation:
    def __init__(
        self,
        operation: AbstractOperation,
        fn: t.Callable,
        uri_parser_class: t.Type[AbstractURIParser],
        api: AbstractAPI,
        operation_id: str,
        pythonic_params: bool,
    ) -> None:
        self._operation = operation
        self._fn = fn
        self.uri_parser_class = uri_parser_class
        self.api = api
        self.operation_id = operation_id
        self.pythonic_params = pythonic_params

    @classmethod
    def from_operation(
        cls, operation: AbstractOperation, pythonic_params: bool
    ) -> "FlaskOperation":
        return cls(
            operation,
            fn=operation.function,
            uri_parser_class=operation.uri_parser_class,
            api=operation.api,
            operation_id=operation.operation_id,
            pythonic_params=pythonic_params,
        )

    @property
    def fn(self) -> t.Callable:
        decorator = FlaskDecorator(
            self._operation,
            uri_parser_cls=self.uri_parser_class,
            pythonic_params=self.pythonic_params,
            jsonifier=self.api.jsonifier,
        )
        return decorator(self._fn)

    def __call__(self, *args, **kwargs) -> FlaskResponse:
        return self.fn(*args, **kwargs)
