"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import collections
import copy
import functools
import logging
import sys

import flask
import six
from jsonschema import (Draft4Validator, ValidationError,
                        draft4_format_checker, validate)
from werkzeug import FileStorage

from ..problem import problem
from ..utils import all_json, boolean, is_null, is_nullable

logger = logging.getLogger('connexion.decorators.validation')

TYPE_MAP = {
    'integer': int,
    'number': float,
    'boolean': boolean
}


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


def make_type(value, type):
    type_func = TYPE_MAP.get(type)  # convert value to right type
    return type_func(value)


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


def validate_parameter_list(parameter_type, request_params, spec_params):
    request_params = set(request_params)
    spec_params = set(spec_params)

    extra_params = request_params.difference(spec_params)

    if extra_params:
        return "Extra {parameter_type} parameter(s) {extra_params} not in spec".format(
            parameter_type=parameter_type, extra_params=', '.join(extra_params))


class RequestBodyValidator(object):
    def __init__(self, schema, consumes, is_null_value_valid=False):
        """
        :param schema: The schema of the request body
        :param consumes: The list of content types the operation consumes
        :param is_nullable: Flag to indicate if null is accepted as valid value.
        """
        self.schema = schema
        self.consumes = consumes
        self.has_default = schema.get('default', False)
        self.is_null_value_valid = is_null_value_valid

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if all_json(self.consumes):
                data = flask.request.json

                logger.debug("%s validating schema...", flask.request.url)
                error = self.validate_schema(data)
                if error and not self.has_default:
                    return error

            response = function(*args, **kwargs)
            return response

        return wrapper

    def validate_schema(self, data):
        """
        :type schema: dict
        :rtype: flask.Response | None
        """
        if self.is_null_value_valid and is_null(data):
            return None

        try:
            validate(data, self.schema, format_checker=draft4_format_checker)
        except ValidationError as exception:
            logger.error("{url} validation error: {error}".format(url=flask.request.url,
                                                                  error=exception.message))
            return problem(400, 'Bad Request', str(exception.message))

        return None


class ResponseBodyValidator(object):
    def __init__(self, schema, has_default=False):
        """
        :param schema: The schema of the response body
        :param has_default: Flag to indicate if default value is present.
        """
        self.schema = schema
        self.has_default = schema.get('default', has_default)

    def validate_schema(self, data):
        """
        :type schema: dict
        :rtype: flask.Response | None
        """
        try:
            validate(data, self.schema, format_checker=draft4_format_checker)
        except ValidationError as exception:
            logger.error("{url} validation error: {error}".format(url=flask.request.url,
                                                                  error=exception))
            six.reraise(*sys.exc_info())

        return None


class ParameterValidator(object):
    def __init__(self, parameters, strict_validation=False):
        """
        :param parameters: List of request parameter dictionaries
        :param strict_validation: Flag indicating if parametrs not in spec are allowed
        """
        self.parameters = collections.defaultdict(list)
        for p in parameters:
            self.parameters[p['in']].append(p)

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
                    validate(converted_value, param, format_checker=draft4_format_checker)
            except ValidationError as exception:
                print(converted_value, type(converted_value), param.get('type'), param, '<--------------------------')
                return str(exception)

        elif param.get('required'):
            return "Missing {parameter_type} parameter '{param[name]}'".format(**locals())

    def validate_query_parameter_list(self):
        request_params = flask.request.args.keys()
        spec_params = [x['name'] for x in self.parameters.get('query', [])]
        return validate_parameter_list('query', request_params, spec_params)

    def validate_formdata_parameter_list(self):
        request_params = flask.request.form.keys()
        spec_params = [x['name'] for x in self.parameters.get('formData', [])]
        return validate_parameter_list('formData', request_params, spec_params)

    def validate_query_parameter(self, param):
        """
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        """
        val = flask.request.args.get(param['name'])
        return self.validate_parameter('query', val, param)

    def validate_path_parameter(self, args, param):
        val = args.get(param['name'].replace('-', '_'))
        return self.validate_parameter('path', val, param)

    def validate_header_parameter(self, param):
        val = flask.request.headers.get(param['name'])
        return self.validate_parameter('header', val, param)

    def validate_formdata_parameter(self, param):
        if param.get('type') == 'file':
            val = flask.request.files.get(param['name'])
        else:
            val = flask.request.form.get(param['name'])

        return self.validate_parameter('formdata', val, param)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            logger.debug("%s validating parameters...", flask.request.url)

            if self.strict_validation:
                error = self.validate_query_parameter_list()
                if error:
                    return problem(400, 'Bad Request', error)

                error = self.validate_formdata_parameter_list()
                if error:
                    return problem(400, 'Bad Request', error)

            for param in self.parameters.get('query', []):
                error = self.validate_query_parameter(param)
                if error:
                    return problem(400, 'Bad Request', error)

            for param in self.parameters.get('path', []):
                error = self.validate_path_parameter(kwargs, param)
                if error:
                    return problem(400, 'Bad Request', error)

            for param in self.parameters.get('header', []):
                error = self.validate_header_parameter(param)
                if error:
                    return problem(400, 'Bad Request', error)

            for param in self.parameters.get('formData', []):
                error = self.validate_formdata_parameter(param)
                if error:
                    return problem(400, 'Bad Request', error)

            response = function(*args, **kwargs)
            return response

        return wrapper
