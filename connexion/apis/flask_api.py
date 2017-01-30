import logging

import connexion.flask_utils as flask_utils
import flask
import werkzeug.exceptions
from connexion.handlers import AuthErrorHandler
from connexion.apis.abstract import AbstractApi

logger = logging.getLogger('connexion.apis.flask_api')


class FlaskApi(AbstractApi):

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
        not_found_error = AuthErrorHandler(werkzeug.exceptions.NotFound(), security=security,
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
        self.blueprint.add_url_rule(flask_path, endpoint_name, operation.function, methods=[method])
