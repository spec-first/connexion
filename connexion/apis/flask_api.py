"""
This module defines a Flask Connexion API which implements translations between Flask and
Connexion requests / responses.
"""

import logging
import warnings
from typing import Any

import flask
import werkzeug.exceptions
from werkzeug.local import LocalProxy

from connexion.apis import flask_utils
from connexion.apis.abstract import AbstractAPI
from connexion.handlers import AuthErrorHandler
from connexion.jsonifier import Jsonifier
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.security import FlaskSecurityHandlerFactory
from connexion.utils import is_json_mimetype

logger = logging.getLogger('connexion.apis.flask_api')


class FlaskApi(AbstractAPI):

    @staticmethod
    def make_security_handler_factory(pass_context_arg_name):
        """ Create default SecurityHandlerFactory to create all security check handlers """
        return FlaskSecurityHandlerFactory(pass_context_arg_name)

    def _set_base_path(self, base_path):
        super()._set_base_path(base_path)
        self._set_blueprint()

    def _set_blueprint(self):
        logger.debug('Creating API blueprint: %s', self.base_path)
        endpoint = flask_utils.flaskify_endpoint(self.base_path)
        self.blueprint = flask.Blueprint(endpoint, __name__, url_prefix=self.base_path,
                                         template_folder=str(self.options.openapi_console_ui_from_dir))

    def add_auth_on_not_found(self, security, security_definitions):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug('Adding path not found authentication')
        not_found_error = AuthErrorHandler(self, werkzeug.exceptions.NotFound(), security=security,
                                           security_definitions=security_definitions)
        endpoint_name = f"{self.blueprint.name}_not_found"
        self.blueprint.add_url_rule('/<path:invalid_path>', endpoint_name, not_found_error.function)

    def _add_operation_internal(self, method, path, operation):
        operation_id = operation.operation_id
        logger.debug('... Adding %s -> %s', method.upper(), operation_id,
                     extra=vars(operation))

        flask_path = flask_utils.flaskify_path(path, operation.get_path_parameter_types())
        endpoint_name = flask_utils.flaskify_endpoint(operation.operation_id,
                                                      operation.randomize_endpoint)
        function = operation.function
        self.blueprint.add_url_rule(flask_path, endpoint_name, function, methods=[method])

    @classmethod
    def get_response(cls, response, mimetype=None, request=None):
        """Gets ConnexionResponse instance for the operation handler
        result. Status Code and Headers for response.  If only body
        data is returned by the endpoint function, then the status
        code will be set to 200 and no headers will be added.

        If the returned object is a flask.Response then it will just
        pass the information needed to recreate it.

        :type response: flask.Response | (flask.Response,) | (flask.Response, int) | (flask.Response, dict) | (flask.Response, int, dict)
        :rtype: ConnexionResponse
        """
        return cls._get_response(response, mimetype=mimetype, extra_context={"url": flask.request.url})

    @classmethod
    def _is_framework_response(cls, response):
        """ Return True if provided response is a framework type """
        return flask_utils.is_flask_response(response)

    @classmethod
    def _framework_to_connexion_response(cls, response, mimetype):
        """ Cast framework response class to ConnexionResponse used for schema validation """
        return ConnexionResponse(
            status_code=response.status_code,
            mimetype=response.mimetype,
            content_type=response.content_type,
            headers=response.headers,
            body=response.get_data() if not response.direct_passthrough else None,
            is_streamed=response.is_streamed
        )

    @classmethod
    def _connexion_to_framework_response(cls, response, mimetype, extra_context=None):
        """ Cast ConnexionResponse to framework response class """
        flask_response = cls._build_response(
            mimetype=response.mimetype or mimetype,
            content_type=response.content_type,
            headers=response.headers,
            status_code=response.status_code,
            data=response.body,
            extra_context=extra_context,
            )

        return flask_response

    @classmethod
    def _build_response(cls, mimetype, content_type=None, headers=None, status_code=None, data=None, extra_context=None):
        if cls._is_framework_response(data):
            return flask.current_app.make_response((data, status_code, headers))

        data, status_code, serialized_mimetype = cls._prepare_body_and_status_code(data=data, mimetype=mimetype, status_code=status_code, extra_context=extra_context)

        kwargs = {
            'mimetype': mimetype or serialized_mimetype,
            'content_type': content_type,
            'headers': headers,
            'response': data,
            'status': status_code
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return flask.current_app.response_class(**kwargs)

    @classmethod
    def _serialize_data(cls, data, mimetype):
        if (isinstance(mimetype, str) and is_json_mimetype(mimetype)):
            body = cls.jsonifier.dumps(data)
        elif not (isinstance(data, bytes) or isinstance(data, str)):
            warnings.warn(
                "Implicit (flask) JSON serialization will change in the next major version. "
                "This is triggered because a response body is being serialized as JSON "
                "even though the mimetype is not a JSON type. "
                "This will be replaced by something that is mimetype-specific and may "
                "raise an error instead of silently converting everything to JSON. "
                "Please make sure to specify media/mime types in your specs.",
                FutureWarning  # a Deprecation targeted at application users.
            )
            body = cls.jsonifier.dumps(data)
        else:
            body = data

        return body, mimetype

    @classmethod
    def get_request(cls, *args, **params):
        # type: (*Any, **Any) -> ConnexionRequest
        """Gets ConnexionRequest instance for the operation handler
        result. Status Code and Headers for response.  If only body
        data is returned by the endpoint function, then the status
        code will be set to 200 and no headers will be added.

        If the returned object is a flask.Response then it will just
        pass the information needed to recreate it.

        :rtype: ConnexionRequest
        """
        context_dict = {}
        setattr(flask._request_ctx_stack.top, 'connexion_context', context_dict)
        flask_request = flask.request
        request = ConnexionRequest(
            flask_request.url,
            flask_request.method,
            headers=flask_request.headers,
            form=flask_request.form,
            query=flask_request.args,
            body=flask_request.get_data(),
            json_getter=lambda: flask_request.get_json(silent=True),
            files=flask_request.files,
            path_params=params,
            context=context_dict,
            cookies=flask_request.cookies,
        )
        logger.debug('Getting data and status code',
                     extra={
                         'data': request.body,
                         'data_type': type(request.body),
                         'url': request.url
                     })
        return request

    @classmethod
    def _set_jsonifier(cls):
        """
        Use Flask specific JSON loader
        """
        cls.jsonifier = Jsonifier(flask.json, indent=2)


def _get_context():
    return getattr(flask._request_ctx_stack.top, 'connexion_context')


context = LocalProxy(_get_context)
