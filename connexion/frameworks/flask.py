import logging

import connexion.api
import connexion.utils as utils
import flask
import werkzeug.exceptions
from connexion.handlers import AuthErrorHandler

logger = logging.getLogger('connexion.frameworks.flask')


class FlaskFramework:
    def __init__(self):
        self.swagger_path = connexion.api.SWAGGER_UI_PATH
        self.swagger_url = connexion.api.SWAGGER_UI_URL

    def get_request(self, *args, **kwargs):
        return flask.request

    def register_app(self, app):
        self.app = app
        self.app.register_blueprint(self.blueprint)

    def set_base_url(self, base_url):
        self.base_url = base_url
        self.blueprint = self._create_blueprint(base_url)

    def register_operation(self, method, path, operation):
        operation_id = operation.operation_id
        logger.debug('... Adding %s -> %s', method.upper(), operation_id,
                     extra=vars(operation))

        flask_path = utils.flaskify_path(path, operation.get_path_parameter_types())
        self.blueprint.add_url_rule(flask_path, operation.endpoint_name, operation.function, methods=[method])

    def register_swagger_json(self, specification):
        """
        Adds swagger json to {base_url}/swagger.json
        """
        logger.debug('Adding swagger.json: %s/swagger.json', self.base_url)
        endpoint_name = "{name}_swagger_json".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/swagger.json',
                                    endpoint_name,
                                    lambda: flask.jsonify(specification))

    def register_swagger_ui(self):
        """
        Adds swagger json to {base_url}/swagger.json
        """
        logger.debug('Adding swagger-ui: %s/%s/', self.base_url, self.swagger_url)
        static_endpoint_name = "{name}_swagger_ui_static".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/{swagger_url}/<path:filename>'.format(swagger_url=self.swagger_url),
                                    static_endpoint_name, self._swagger_ui_static)
        index_endpoint_name = "{name}_swagger_ui_index".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/{swagger_url}/'.format(swagger_url=self.swagger_url),
                                    index_endpoint_name, self._swagger_ui_index)

    def register_auth_on_not_found(self):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """
        logger.debug('Adding path not found authentication')
        not_found_error = AuthErrorHandler(werkzeug.exceptions.NotFound(), security=self.security,
                                           security_definitions=self.security_definitions)
        endpoint_name = "{name}_not_found".format(name=self.blueprint.name)
        self.blueprint.add_url_rule('/<path:invalid_path>', endpoint_name, not_found_error.function)

    def _create_blueprint(self, base_url):
        """
        :type base_url: str | None
        :rtype: flask.Blueprint
        """
        logger.debug('Creating API blueprint: %s', base_url)
        endpoint = utils.flaskify_endpoint(base_url)
        blueprint = flask.Blueprint(endpoint, __name__, url_prefix=base_url,
                                    template_folder=str(self.swagger_path))
        return blueprint

    def _swagger_ui_index(self):
        return flask.render_template('index.html', api_url=self.base_url)

    def _swagger_ui_static(self, filename):
        """
        :type filename: str
        """
        return flask.send_from_directory(str(self.swagger_path), filename)
