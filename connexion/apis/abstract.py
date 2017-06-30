import abc
import copy
import logging
import pathlib
import sys
from typing import AnyStr, List  # NOQA

import jinja2
import six
import yaml
from swagger_spec_validator.validator20 import validate_spec

from ..exceptions import ResolverError
from ..operation import Operation
from ..options import ConnexionOptions
from ..resolver import Resolver

MODULE_PATH = pathlib.Path(__file__).absolute().parent.parent
SWAGGER_UI_PATH = MODULE_PATH / 'vendor' / 'swagger-ui'
SWAGGER_UI_URL = 'ui'

RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS = 6

logger = logging.getLogger('connexion.apis.abstract')


@six.add_metaclass(abc.ABCMeta)
class AbstractAPI(object):
    """
    Defines an abstract interface for a Swagger API
    """

    def __init__(self, specification, base_path=None, arguments=None,
                 validate_responses=False, strict_validation=False, resolver=None,
                 auth_all_paths=False, debug=False, resolver_error_handler=None,
                 validator_map=None, pythonic_params=False, options=None, **old_style_options):
        """
        :type specification: pathlib.Path | dict
        :type base_path: str | None
        :type arguments: dict | None
        :type validate_responses: bool
        :type strict_validation: bool
        :type auth_all_paths: bool
        :type debug: bool
        :param validator_map: Custom validators for the types "parameter", "body" and "response".
        :type validator_map: dict
        :param resolver: Callable that maps operationID to a function
        :param resolver_error_handler: If given, a callable that generates an
            Operation used for handling ResolveErrors
        :type resolver_error_handler: callable | None
        :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended
        to any shadowed built-ins
        :type pythonic_params: bool
        :param options: New style options dictionary.
        :type options: dict | None
        :param old_style_options: Old style options support for backward compatibility. Preference is
                                  what is defined in `options` parameter.
        """
        self.debug = debug
        self.validator_map = validator_map
        self.resolver_error_handler = resolver_error_handler

        self.options = ConnexionOptions(old_style_options)
        # options is added last to preserve the highest priority
        self.options = self.options.extend(options)

        # TODO: Remove this in later versions (Current version is 1.1.9)
        if base_path is None and 'base_url' in old_style_options:
            base_path = old_style_options['base_url']
            logger.warning("Parameter base_url should be no longer used. Use base_path instead.")

        logger.debug('Loading specification: %s', specification,
                     extra={'swagger_yaml': specification,
                            'base_path': base_path,
                            'arguments': arguments,
                            'swagger_ui': self.options.openapi_console_ui_available,
                            'swagger_path': self.options.openapi_console_ui_from_dir,
                            'swagger_url': self.options.openapi_console_ui_path,
                            'auth_all_paths': auth_all_paths})

        if isinstance(specification, dict):
            self.specification = specification
        else:
            specification_path = pathlib.Path(specification)
            self.specification = self.load_spec_from_file(arguments, specification_path)

        self.specification = compatibility_layer(self.specification)
        logger.debug('Read specification', extra={'spec': self.specification})

        # Avoid validator having ability to modify specification
        spec = copy.deepcopy(self.specification)
        validate_spec(spec)

        # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#fixed-fields
        # If base_path is not on provided then we try to read it from the swagger.yaml or use / by default
        self._set_base_path(base_path)

        # A list of MIME types the APIs can produce. This is global to all APIs but can be overridden on specific
        # API calls.
        self.produces = self.specification.get('produces', list())  # type: List[str]

        # A list of MIME types the APIs can consume. This is global to all APIs but can be overridden on specific
        # API calls.
        self.consumes = self.specification.get('consumes', ['application/json'])  # type: List[str]

        self.security = self.specification.get('security')
        self.security_definitions = self.specification.get('securityDefinitions', dict())
        logger.debug('Security Definitions: %s', self.security_definitions)

        self.definitions = self.specification.get('definitions', {})
        self.parameter_definitions = self.specification.get('parameters', {})
        self.response_definitions = self.specification.get('responses', {})

        self.resolver = resolver or Resolver()

        logger.debug('Validate Responses: %s', str(validate_responses))
        self.validate_responses = validate_responses

        logger.debug('Strict Request Validation: %s', str(validate_responses))
        self.strict_validation = strict_validation

        logger.debug('Pythonic params: %s', str(pythonic_params))
        self.pythonic_params = pythonic_params

        if self.options.openapi_spec_available:
            self.add_swagger_json()

        if self.options.openapi_console_ui_available:
            self.add_swagger_ui()

        self.add_paths()

        if auth_all_paths:
            self.add_auth_on_not_found(self.security, self.security_definitions)

    def _set_base_path(self, base_path):
        # type: (AnyStr) -> None
        if base_path is None:
            self.base_path = canonical_base_path(self.specification.get('basePath', ''))
        else:
            self.base_path = canonical_base_path(base_path)
            self.specification['basePath'] = base_path

    @abc.abstractmethod
    def add_swagger_json(self):
        """
        Adds swagger json to {base_path}/swagger.json
        """

    @abc.abstractmethod
    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_path}/ui/
        """

    @abc.abstractmethod
    def add_auth_on_not_found(self, security, security_definitions):
        """
        Adds a 404 error handler to authenticate and only expose the 404 status if the security validation pass.
        """

    def add_operation(self, method, path, swagger_operation, path_parameters):
        """
        Adds one operation to the api.

        This method uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.

        :type method: str
        :type path: str
        :type swagger_operation: dict
        """
        operation = Operation(self,
                              method=method,
                              path=path,
                              path_parameters=path_parameters,
                              operation=swagger_operation,
                              app_produces=self.produces,
                              app_consumes=self.consumes,
                              app_security=self.security,
                              security_definitions=self.security_definitions,
                              definitions=self.definitions,
                              parameter_definitions=self.parameter_definitions,
                              response_definitions=self.response_definitions,
                              validate_responses=self.validate_responses,
                              validator_map=self.validator_map,
                              strict_validation=self.strict_validation,
                              resolver=self.resolver,
                              pythonic_params=self.pythonic_params)
        self._add_operation_internal(method, path, operation)

    @abc.abstractmethod
    def _add_operation_internal(self, method, path, operation):
        """
        Adds the operation according to the user framework in use.
        It will be used to register the operation on the user framework router.
        """

    def _add_resolver_error_handler(self, method, path, err):
        """
        Adds a handler for ResolverError for the given method and path.
        """
        operation = self.resolver_error_handler(err,
                                                method=method,
                                                path=path,
                                                app_produces=self.produces,
                                                app_security=self.security,
                                                security_definitions=self.security_definitions,
                                                definitions=self.definitions,
                                                parameter_definitions=self.parameter_definitions,
                                                response_definitions=self.response_definitions,
                                                validate_responses=self.validate_responses,
                                                strict_validation=self.strict_validation,
                                                resolver=self.resolver,
                                                randomize_endpoint=RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS)
        self._add_operation_internal(method, path, operation)

    def add_paths(self, paths=None):
        """
        Adds the paths defined in the specification as endpoints

        :type paths: list
        """
        paths = paths or self.specification.get('paths', dict())
        for path, methods in paths.items():
            logger.debug('Adding %s%s...', self.base_path, path)

            # search for parameters definitions in the path level
            # http://swagger.io/specification/#pathItemObject
            path_parameters = methods.get('parameters', [])

            for method, endpoint in methods.items():
                if method == 'parameters':
                    continue
                try:
                    self.add_operation(method, path, endpoint, path_parameters)
                except ResolverError as err:
                    # If we have an error handler for resolver errors, add it as an operation.
                    # Otherwise treat it as any other error.
                    if self.resolver_error_handler is not None:
                        self._add_resolver_error_handler(method, path, err)
                    else:
                        self._handle_add_operation_error(path, method, err.exc_info)
                except Exception:
                    # All other relevant exceptions should be handled as well.
                    self._handle_add_operation_error(path, method, sys.exc_info())

    def _handle_add_operation_error(self, path, method, exc_info):
        url = '{base_path}{path}'.format(base_path=self.base_path, path=path)
        error_msg = 'Failed to add operation for {method} {url}'.format(
            method=method.upper(),
            url=url)
        if self.debug:
            logger.exception(error_msg)
        else:
            logger.error(error_msg)
            six.reraise(*exc_info)

    def load_spec_from_file(self, arguments, specification):
        arguments = arguments or {}

        with specification.open(mode='rb') as swagger_yaml:
            contents = swagger_yaml.read()
            try:
                swagger_template = contents.decode()
            except UnicodeDecodeError:
                swagger_template = contents.decode('utf-8', 'replace')

            swagger_string = jinja2.Template(swagger_template).render(**arguments)
            return yaml.safe_load(swagger_string)  # type: dict

    @classmethod
    @abc.abstractmethod
    def get_request(self, *args, **kwargs):
        """
        This method converts the user framework request to a ConnexionRequest.
        """

    @classmethod
    @abc.abstractmethod
    def get_response(self, response, mimetype=None, request=None):
        """
        This method converts the ConnexionResponse to a user framework response.
        :param response: A response to cast.
        :param mimetype: The response mimetype.
        :param request: The request associated with this response (the user framework request).

        :type response: ConnexionResponse
        :type mimetype: str
        """

    @classmethod
    @abc.abstractmethod
    def json_loads(self, data):
        """
        API specific JSON loader.

        :param data:
        :return:
        """


def canonical_base_path(base_path):
    """
    Make given "basePath" a canonical base URL which can be prepended to paths starting with "/".
    """
    return base_path.rstrip('/')


def compatibility_layer(spec):
    """Make specs compatible with older versions of Connexion."""
    if not isinstance(spec, dict):
        return spec

    # Make all response codes be string
    for path_name, methods_available in spec.get('paths', {}).items():
        for method_name, method_def in methods_available.items():
            if (method_name == 'parameters' or not isinstance(
                    method_def, dict)):
                continue

            response_definitions = {}
            for response_code, response_def in method_def.get(
                    'responses', {}).items():
                response_definitions[str(response_code)] = response_def

            method_def['responses'] = response_definitions
    return spec
