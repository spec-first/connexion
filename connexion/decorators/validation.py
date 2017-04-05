import collections
import copy
import functools
import logging
import sys

import six
from jsonschema import Draft4Validator, ValidationError, draft4_format_checker
from werkzeug import FileStorage

from ..exceptions import ExtraParameterProblem
from ..problem import problem
from ..utils import all_json, boolean, is_null, is_nullable

logger = logging.getLogger('connexion.decorators.validation')

TYPE_MAP = {
    'integer': int,
    'number': float,
    'boolean': boolean
}


def make_type(value, type_literal):
    type_func = TYPE_MAP.get(type_literal)
    return type_func(value)


class TypeValidationError(Exception):
    def __init__(self, schema_type, parameter_type, parameter_name):
        """
        Exception raise when type validation fails

        :type schema_type: str
        :type parameter_type: str
        :type parameter_name: str
        :return:
        """
        self.schema_type = schema_type
        self.parameter_type = parameter_type
        self.parameter_name = parameter_name

    def __str__(self):
        msg = "Wrong type, expected '{schema_type}' for {parameter_type} parameter '{parameter_name}'"
        return msg.format(**vars(self))


def validate_type(param, value, parameter_type, parameter_name=None):
    param_type = param.get('type')
    parameter_name = parameter_name if parameter_name else param['name']
    if param_type == "array":  # then logic is more complex
        if param.get("collectionFormat") and param.get("collectionFormat") == "pipes":
            parts = value.split("|")
        else:  # default: csv
            parts = value.split(",")

        converted_parts = []
        for part in parts:
            try:
                converted = make_type(part, param["items"]["type"])
            except (ValueError, TypeError):
                converted = part
            converted_parts.append(converted)
        return converted_parts
    else:
        try:
            return make_type(value, param_type)
        except ValueError:
            raise TypeValidationError(param_type, parameter_type, parameter_name)
        except TypeError:
            return value


def validate_parameter_list(request_params, spec_params):
    request_params = set(request_params)
    spec_params = set(spec_params)

    return request_params.difference(spec_params)


class RequestBodyValidator(object):
    def __init__(self, schema, consumes, api, is_null_value_valid=False, validator=None):
        """
        :param schema: The schema of the request body
        :param consumes: The list of content types the operation consumes
        :param is_null_value_valid: Flag to indicate if null is accepted as valid value.
        :param validator: Validator class that should be used to validate passed data
                          against API schema. Default is jsonschema.Draft4Validator.
        :type validator: jsonschema.IValidator
        """
        self.consumes = consumes
        self.has_default = schema.get('default', False)
        self.is_null_value_valid = is_null_value_valid
        validatorClass = validator or Draft4Validator
        self.validator = validatorClass(schema, format_checker=draft4_format_checker)
        self.api = api

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            if all_json(self.consumes):
                data = request.json

                if data is None and len(request.body) > 0 and not self.is_null_value_valid:
                    # the body has contents that were not parsed as JSON
                    return problem(415,
                                   "Unsupported Media Type",
                                   "Invalid Content-type ({content_type}), expected JSON data".format(
                                       content_type=request.headers["Content-Type"]
                                   ))

                logger.debug("%s validating schema...", request.url)
                error = self.validate_schema(data, request.url)
                if error and not self.has_default:
                    return error

            response = function(request)
            return response

        return wrapper

    def validate_schema(self, data, url):
        # type: (dict, AnyStr) -> Union[ConnexionResponse, None]
        if self.is_null_value_valid and is_null(data):
            return None

        try:
            self.validator.validate(data)
        except ValidationError as exception:
            logger.error("{url} validation error: {error}".format(url=url,
                                                                  error=exception.message))
            return problem(400, 'Bad Request', str(exception.message))

        return None


class ResponseBodyValidator(object):
    def __init__(self, schema, validator=None):
        """
        :param schema: The schema of the response body
        :param validator: Validator class that should be used to validate passed data
                          against API schema. Default is jsonschema.Draft4Validator.
        :type validator: jsonschema.IValidator
        """
        ValidatorClass = validator or Draft4Validator
        self.validator = ValidatorClass(schema, format_checker=draft4_format_checker)

    def validate_schema(self, data, url):
        # type: (dict, AnyStr) -> Union[ConnexionResponse, None]
        try:
            self.validator.validate(data)
        except ValidationError as exception:
            logger.error("{url} validation error: {error}".format(url=url,
                                                                  error=exception))
            six.reraise(*sys.exc_info())

        return None


class ParameterValidator(object):
    def __init__(self, parameters, api, strict_validation=False):
        """
        :param parameters: List of request parameter dictionaries
        :param strict_validation: Flag indicating if parameters not in spec are allowed
        """
        self.parameters = collections.defaultdict(list)
        for p in parameters:
            self.parameters[p['in']].append(p)

        self.api = api
        self.strict_validation = strict_validation

    @staticmethod
    def validate_parameter(parameter_type, value, param):
        if value is not None:
            if is_nullable(param) and is_null(value):
                return

            try:
                converted_value = validate_type(param, value, parameter_type)
            except TypeValidationError as e:
                return str(e)

            param = copy.deepcopy(param)
            if 'required' in param:
                del param['required']
            try:
                if parameter_type == 'formdata' and param.get('type') == 'file':
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

    def validate_formdata_parameter(self, param, request):
        if param.get('type') == 'file':
            val = request.files.get(param['name'])
        else:
            val = request.form.get(param['name'])

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
                    response = problem(400, 'Bad Request', error)
                    return self.api.get_response(response)

            for param in self.parameters.get('path', []):
                error = self.validate_path_parameter(param, request)
                if error:
                    response = problem(400, 'Bad Request', error)
                    return self.api.get_response(response)

            for param in self.parameters.get('header', []):
                error = self.validate_header_parameter(param, request)
                if error:
                    response = problem(400, 'Bad Request', error)
                    return self.api.get_response(response)

            for param in self.parameters.get('formData', []):
                error = self.validate_formdata_parameter(param, request)
                if error:
                    response = problem(400, 'Bad Request', error)
                    return self.api.get_response(response)

            return function(request)

        return wrapper
