import collections
import copy
import functools
import logging
import sys

import pkg_resources
import six
from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from jsonschema.validators import extend
from werkzeug.datastructures import FileStorage

from ..exceptions import ExtraParameterProblem, BadRequestProblem, UnsupportedMediaTypeProblem
from ..http_facts import FORM_CONTENT_TYPES
from ..json_schema import Draft4RequestValidator, Draft4ResponseValidator
from ..content_types import ContentHandlerFactory
from ..types import TypeValidationError, coerce_type
from ..utils import all_json, boolean, is_json_mimetype, is_null, is_nullable

_jsonschema_3_or_newer = pkg_resources.parse_version(
        pkg_resources.get_distribution("jsonschema").version) >= \
    pkg_resources.parse_version("3.0.0")

logger = logging.getLogger('connexion.decorators.validation')


def validate_parameter_list(request_params, spec_params):
    request_params = set(request_params)
    spec_params = set(spec_params)

    return request_params.difference(spec_params)


class RequestBodyValidator(object):

    def __init__(self, schema, consumes, api, is_null_value_valid=False, validator=None,
                 strict_validation=False):
        """
        :param schema: The schema of the request body
        :param consumes: The list of content types the operation consumes
        :param is_null_value_valid: Flag to indicate if null is accepted as valid value.
        :param validator: Validator class that should be used to validate passed data
                          against API schema. Default is jsonschema.Draft4Validator.
        :type validator: jsonschema.IValidator
        :param strict_validation: Flag indicating if parameters not in spec are allowed
        """
        self.consumes = consumes
        self.schema = schema
        self.has_default = schema.get('default', False)
        self.is_null_value_valid = is_null_value_valid
        validatorClass = validator or Draft4RequestValidator
        self.validator = validatorClass(schema, format_checker=draft4_format_checker)
        self.api = api
        self.strict_validation = strict_validation
        self.content_handler_factory = ContentHandlerFactory(
            self.validator,
            self.schema,
            self.strict_validation,
            self.is_null_value_valid,
            self.consumes
        )

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            content_handler = self.content_handler_factory.get_handler(request.content_type)
            if content_handler is None:
                raise UnsupportedMediaTypeProblem(
                    "Unsupported Content-type ({content_type})".format(
                        content_type=request.headers.get("Content-Type", "")
                    ))

            content_handler.validate_request(request)

            response = function(request)
            return response

        return wrapper


class ResponseBodyValidator(object):
    def __init__(self, schema, validator=None):
        """
        :param schema: The schema of the response body
        :param validator: Validator class that should be used to validate passed data
                          against API schema. Default is jsonschema.Draft4Validator.
        :type validator: jsonschema.IValidator
        """
        ValidatorClass = validator or Draft4ResponseValidator
        self.validator = ValidatorClass(schema, format_checker=draft4_format_checker)

    def validate_schema(self, data, url):
        # type: (dict, AnyStr) -> Union[ConnexionResponse, None]
        try:
            self.validator.validate(data)
        except ValidationError as exception:
            logger.error("{url} validation error: {error}".format(url=url,
                                                                  error=exception),
                         extra={'validator': 'response'})
            six.reraise(*sys.exc_info())

        return None


class ParameterValidator(object):
    def __init__(self, parameters, api, strict_validation=False):
        """
        :param parameters: List of request parameter dictionaries
        :param api: api that the validator is attached to
        :param strict_validation: Flag indicating if parameters not in spec are allowed
        """
        self.parameters = collections.defaultdict(list)
        for p in parameters:
            self.parameters[p['in']].append(p)

        self.api = api
        self.strict_validation = strict_validation

    @staticmethod
    def validate_parameter(parameter_type, value, param, param_name=None):
        if value is not None:
            if is_nullable(param) and is_null(value):
                return

            try:
                converted_value = coerce_type(param, value, parameter_type, param_name)
            except TypeValidationError as e:
                return str(e)

            param = copy.deepcopy(param)
            param = param.get('schema', param)
            if 'required' in param:
                del param['required']
            try:
                if parameter_type == 'formdata' and param.get('type') == 'file':
                    if _jsonschema_3_or_newer:
                        extend(
                            Draft4Validator,
                            type_checker=Draft4Validator.TYPE_CHECKER.redefine(
                                "file",
                                lambda checker, instance: isinstance(instance, FileStorage)
                            )
                        )(param, format_checker=draft4_format_checker).validate(converted_value)
                    else:
                        Draft4Validator(
                            param,
                            format_checker=draft4_format_checker,
                            types={'file': FileStorage}).validate(converted_value)
                else:
                    Draft4Validator(
                        param, format_checker=draft4_format_checker).validate(converted_value)
            except ValidationError as exception:
                debug_msg = 'Error while converting value {converted_value} from param ' \
                            '{type_converted_value} of type real type {param_type} to the declared type {param}'
                fmt_params = dict(
                    converted_value=str(converted_value),
                    type_converted_value=type(converted_value),
                    param_type=param.get('type'),
                    param=param
                )
                logger.info(debug_msg.format(**fmt_params))
                return str(exception)

        elif param.get('required'):
            return "Missing {parameter_type} parameter '{param[name]}'".format(**locals())

    def validate_query_parameter_list(self, request):
        request_params = request.query.keys()
        spec_params = [x['name'] for x in self.parameters.get('query', [])]
        return validate_parameter_list(request_params, spec_params)

    def validate_formdata_parameter_list(self, request):
        request_params = request.form.keys()
        spec_params = [x['name'] for x in self.parameters.get('formData', [])]
        return validate_parameter_list(request_params, spec_params)

    def validate_query_parameter(self, param, request):
        """
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        """
        val = request.query.get(param['name'])
        return self.validate_parameter('query', val, param)

    def validate_path_parameter(self, param, request):
        val = request.path_params.get(param['name'].replace('-', '_'))
        return self.validate_parameter('path', val, param)

    def validate_header_parameter(self, param, request):
        val = request.headers.get(param['name'])
        return self.validate_parameter('header', val, param)

    def validate_cookie_parameter(self, param, request):
        val = request.cookies.get(param['name'])
        return self.validate_parameter('cookie', val, param)

    def validate_formdata_parameter(self, param_name, param, request):
        if param.get('type') == 'file' or param.get('format') == 'binary':
            val = request.files.get(param_name)
        else:
            val = request.form.get(param_name)

        return self.validate_parameter('formdata', val, param)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            logger.debug("%s validating parameters...", request.url)

            if self.strict_validation:
                query_errors = self.validate_query_parameter_list(request)
                formdata_errors = self.validate_formdata_parameter_list(request)

                if formdata_errors or query_errors:
                    raise ExtraParameterProblem(formdata_errors, query_errors)

            for param in self.parameters.get('query', []):
                error = self.validate_query_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('path', []):
                error = self.validate_path_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('header', []):
                error = self.validate_header_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('cookie', []):
                error = self.validate_cookie_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('formData', []):
                error = self.validate_formdata_parameter(param["name"], param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            return function(request)

        return wrapper
