"""
This module defines view function decorators to validate request and response parameters and bodies.
"""

import collections
import copy
import functools
import logging

from jsonschema import Draft4Validator, ValidationError, draft4_format_checker

from ..exceptions import BadRequestProblem, ExtraParameterProblem
from ..utils import boolean, is_null, is_nullable

logger = logging.getLogger("connexion.decorators.validation")

TYPE_MAP = {"integer": int, "number": float, "boolean": boolean, "object": dict}


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


def coerce_type(param, value, parameter_type, parameter_name=None):
    def make_type(value, type_literal):
        type_func = TYPE_MAP.get(type_literal)
        return type_func(value)

    param_schema = param.get("schema", param)
    if is_nullable(param_schema) and is_null(value):
        return None

    param_type = param_schema.get("type")
    parameter_name = parameter_name if parameter_name else param.get("name")
    if param_type == "array":
        converted_params = []
        if parameter_type == "header":
            value = value.split(",")
        for v in value:
            try:
                converted = make_type(v, param_schema["items"]["type"])
            except (ValueError, TypeError):
                converted = v
            converted_params.append(converted)
        return converted_params
    elif param_type == "object":
        if param_schema.get("properties"):

            def cast_leaves(d, schema):
                if type(d) is not dict:
                    try:
                        return make_type(d, schema["type"])
                    except (ValueError, TypeError):
                        return d
                for k, v in d.items():
                    if k in schema["properties"]:
                        d[k] = cast_leaves(v, schema["properties"][k])
                return d

            return cast_leaves(value, param_schema)
        return value
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


class ParameterValidator:
    def __init__(self, parameters, api, strict_validation=False):
        """
        :param parameters: List of request parameter dictionaries
        :param api: api that the validator is attached to
        :param strict_validation: Flag indicating if parameters not in spec are allowed
        """
        self.parameters = collections.defaultdict(list)
        for p in parameters:
            self.parameters[p["in"]].append(p)

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
            param = param.get("schema", param)
            if "required" in param:
                del param["required"]
            try:
                Draft4Validator(param, format_checker=draft4_format_checker).validate(
                    converted_value
                )
            except ValidationError as exception:
                debug_msg = (
                    "Error while converting value {converted_value} from param "
                    "{type_converted_value} of type real type {param_type} to the declared type {param}"
                )
                fmt_params = dict(
                    converted_value=str(converted_value),
                    type_converted_value=type(converted_value),
                    param_type=param.get("type"),
                    param=param,
                )
                logger.info(debug_msg.format(**fmt_params))
                return str(exception)

        elif param.get("required"):
            return "Missing {parameter_type} parameter '{param[name]}'".format(
                **locals()
            )

    def validate_query_parameter_list(self, request):
        request_params = request.query.keys()
        spec_params = [x["name"] for x in self.parameters.get("query", [])]
        return validate_parameter_list(request_params, spec_params)

    def validate_query_parameter(self, param, request):
        """
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        """
        val = request.query.get(param["name"])
        return self.validate_parameter("query", val, param)

    def validate_path_parameter(self, param, request):
        val = request.path_params.get(param["name"].replace("-", "_"))
        return self.validate_parameter("path", val, param)

    def validate_header_parameter(self, param, request):
        val = request.headers.get(param["name"])
        return self.validate_parameter("header", val, param)

    def validate_cookie_parameter(self, param, request):
        val = request.cookies.get(param["name"])
        return self.validate_parameter("cookie", val, param)

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

                if query_errors:
                    raise ExtraParameterProblem([], query_errors)

            for param in self.parameters.get("query", []):
                error = self.validate_query_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get("path", []):
                error = self.validate_path_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get("header", []):
                error = self.validate_header_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get("cookie", []):
                error = self.validate_cookie_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            return function(request)

        return wrapper
