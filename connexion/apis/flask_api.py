import logging

import flask
import six
import werkzeug.exceptions

from connexion.apis import flask_utils
from connexion.apis.abstract import AbstractAPI
from connexion.decorators.produces import BaseSerializer, NoContent
from connexion.handlers import AuthErrorHandler
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.utils import is_json_mimetype

logger = logging.getLogger('connexion.apis.flask_api')


class Jsonifier(BaseSerializer):
    @staticmethod
    def dumps(data):
        """ Central point where JSON serialization happens inside
        Connexion.
        """
        return "{}\n".format(flask.json.dumps(data, indent=2))

    @staticmethod
    def loads(data):
        """ Central point where JSON serialization happens inside
        Connexion.
        """
        if isinstance(data, six.binary_type):
            data = data.decode()

        try:
            return flask.json.loads(data)
        except Exception as error:
            if isinstance(data, six.string_types):
                return data

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Jsonifier: {}>'.format(self.mimetype)


class FlaskApi(AbstractAPI):
    jsonifier = Jsonifier

    def __init__(self, specification, base_url=None, arguments=None,
                 swagger_json=None, swagger_ui=None, swagger_path=None, swagger_url=None,
                 validate_responses=False, strict_validation=False, resolver=None,
                 auth_all_paths=False, debug=False, resolver_error_handler=None,
                 validator_map=None, pythonic_params=False):
        super(FlaskApi, self).__init__(
            specification, FlaskApi.jsonifier, base_url=base_url, arguments=arguments,
            swagger_json=swagger_json, swagger_ui=swagger_ui,
            swagger_path=swagger_path, swagger_url=swagger_url,
            validate_responses=validate_responses, strict_validation=strict_validation,
            resolver=resolver, auth_all_paths=auth_all_paths, debug=debug,
            resolver_error_handler=resolver_error_handler, validator_map=validator_map,
            pythonic_params=pythonic_params
        )

    def _set_base_url(self, base_url):
        super(FlaskApi, self)._set_base_url(base_url)
        self._set_blueprint()

    def _set_blueprint(self):
        logger.debug('Creating API blueprint: %s', self.base_url)
        endpoint = flask_utils.flaskify_endpoint(self.base_url)
        self.blueprint = flask.Blueprint(endpoint, __name__, url_prefix=self.base_url,
                                         template_folder=str(self.swagger_path))

    def add_swagger_json(self):
        """
        Adds swagger json to {base_url}/swagger.json
        """
        logger.debug('Adding swagger.json: %s/swagger.json', self.base_url)
        endpoint_name = "{name}_swagger_json".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/swagger.json',
                                    endpoint_name,
                                    lambda: flask.jsonify(self.specification))

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_url}/ui/
        """
        logger.debug('Adding swagger-ui: %s/%s/', self.base_url, self.swagger_url)
        static_endpoint_name = "{name}_swagger_ui_static".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/{swagger_url}/<path:filename>'.format(swagger_url=self.swagger_url),
                                    static_endpoint_name, self.swagger_ui_static)
        index_endpoint_name = "{name}_swagger_ui_index".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/{swagger_url}/'.format(swagger_url=self.swagger_url),
                                    index_endpoint_name, self.swagger_ui_index)

    def swagger_ui_index(self):
        return flask.render_template('index.html', api_url=self.base_url)

    def swagger_ui_static(self, filename):
        """
        :type filename: str
        """
        return flask.send_from_directory(str(self.swagger_path), filename)

    def add_auth_on_not_found(self, security, security_definitions):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug('Adding path not found authentication')
        not_found_error = AuthErrorHandler(self, werkzeug.exceptions.NotFound(), security=security,
                                           security_definitions=security_definitions)
        endpoint_name = "{name}_not_found".format(name=self.blueprint.name)
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

        :type operation_handler_result: flask.Response | (flask.Response, int) | (flask.Response, int, dict)
        :rtype: ConnexionRequest
        """
        logger.debug('Getting data and status code',
                     extra={
                         'data': response,
                         'data_type': type(response),
                         'url': flask.request.url
                     })

        if isinstance(response, ConnexionResponse):
            flask_response = cls._get_flask_response_from_connexion(response, mimetype)
        else:
            flask_response = cls._get_flask_response(response, mimetype)

        logger.debug('Got data and status code (%d)',
                     flask_response.status_code,
                     extra={
                         'data': response,
                         'datatype': type(response),
                         'url': flask.request.url
                     })

        return flask_response

    @classmethod
    def _get_flask_response_from_connexion(cls, response, mimetype):
        data = response.body
        status_code = response.status_code
        mimetype = response.mimetype or mimetype
        content_type = response.content_type or mimetype
        headers = response.headers

        flask_response = cls._build_flask_response(mimetype, content_type,
                                                   headers, status_code, data)

        return flask_response

    @classmethod
    def _build_flask_response(cls, mimetype=None, content_type=None,
                              headers=None, status_code=None, data=None):
        kwargs = {
            'mimetype': mimetype,
            'content_type': content_type,
            'headers': headers
        }
        kwargs = {k: v for k, v in six.iteritems(kwargs) if v is not None}
        flask_response = flask.current_app.response_class(**kwargs)  # type: flask.Response

        if status_code is not None:
            flask_response.status_code = status_code

        if data is not None and data is not NoContent:
            data = cls._jsonify_data(data, mimetype)
            flask_response.set_data(data)

        elif data is NoContent:
                flask_response.set_data('')

        return flask_response

    @classmethod
    def _jsonify_data(cls, data, mimetype):
        if (isinstance(mimetype, six.string_types) and is_json_mimetype(mimetype)) \
                or not (isinstance(data, six.binary_type) or isinstance(data, six.text_type)):
            return cls.jsonifier.dumps(data)

        return data

    @classmethod
    def _get_flask_response(cls, response, mimetype):
        if flask_utils.is_flask_response(response):
            return response

        elif isinstance(response, tuple) and flask_utils.is_flask_response(response[0]):
            return flask.current_app.make_response(response)

        elif isinstance(response, tuple) and len(response) == 3:
            data, status_code, headers = response
            return cls._build_flask_response(mimetype, None,
                                             headers, status_code, data)

        elif isinstance(response, tuple) and len(response) == 2:
            data, status_code = response
            return cls._build_flask_response(mimetype, None, None,
                                             status_code, data)

        else:
            return cls._build_flask_response(mimetype=mimetype, data=response)

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
        flask_request = flask.request
        request = ConnexionRequest(
            flask_request.url,
            flask_request.method,
            headers=flask_request.headers,
            form=flask_request.form,
            query=flask_request.args,
            body=flask_request.get_data(),
            json=flask_request.get_json(silent=True),
            files=flask_request.files,
            path_params=params,
            context=FlaskRequestContextProxy()
        )
        logger.debug('Getting data and status code',
                     extra={
                         'data': request.body,
                         'data_type': type(request.body),
                         'url': request.url
                     })
        return request


class FlaskRequestContextProxy(object):
    """"Proxy assignments from `ConnexionRequest.context`
    to `flask.request` instance.
    """
    def __init__(self):
        self.values = {}

    def __setitem__(self, key, value):
        # type: (str, Any) -> None
        logger.debug('Setting "%s" attribute in flask.request', key)
        setattr(flask.request, key, value)
        self.values[key] = value

    def items(self):
        # type: () -> list
        return self.values.items()
