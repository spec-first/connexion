import copy
import functools
import inspect
import logging

import flask
import six
import werkzeug.exceptions as exceptions

from ..utils import boolean, is_null, is_nullable

logger = logging.getLogger(__name__)

# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': float,
            'string': str,
            'boolean': boolean,
            'array': list,
            'object': dict}  # map of swagger types to python types


def get_function_arguments(function):  # pragma: no cover
    """
    Returns the list of arguments of a function

    :type function: Callable
    :rtype: list[str]
    """
    if six.PY3:
        return list(inspect.signature(function).parameters)
    else:
        return inspect.getargspec(function).args


def make_type(value, type):
    type_func = TYPE_MAP[type]  # convert value to right type
    return type_func(value)


def get_val_from_param(value, query_param):
    if is_nullable(query_param) and is_null(value):
        return None

    if query_param["type"] == "array":  # then logic is more complex
        if query_param.get("collectionFormat") and query_param.get("collectionFormat") == "pipes":
            parts = value.split("|")
        else:  # default: csv
            parts = value.split(",")
        return [make_type(part, query_param["items"]["type"]) for part in parts]
    else:
        return make_type(value, query_param["type"])


def parameter_to_arg(parameters, function):
    """
    Pass query and body parameters as keyword arguments to handler function.

    See (https://github.com/zalando/connexion/issues/59)
    :param parameters: All the parameters of the handler functions
    :type parameters: dict|None
    :param function: The handler function for the REST endpoint.
    :type function: function|None
    """
    body_parameters = [parameter for parameter in parameters if parameter['in'] == 'body'] or [{}]
    body_name = body_parameters[0].get('name')
    default_body = body_parameters[0].get('schema', {}).get('default')
    query_types = {parameter['name']: parameter
                   for parameter in parameters if parameter['in'] == 'query'}  # type: dict[str, str]
    form_types = {parameter['name']: parameter
                  for parameter in parameters if parameter['in'] == 'formData'}
    path_types = {parameter['name']: parameter
                  for parameter in parameters if parameter['in'] == 'path'}
    arguments = get_function_arguments(function)
    default_query_params = {param['name']: param['default']
                            for param in parameters if param['in'] == 'query' and 'default' in param}
    default_form_params = {param['name']: param['default']
                           for param in parameters if param['in'] == 'formData' and 'default' in param}

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug('Function Arguments: %s', arguments)

        try:
            request_body = flask.request.json
        except exceptions.BadRequest:
            request_body = None

        if default_body and not request_body:
            request_body = default_body

        # Parse path parameters
        for key, path_param_definitions in path_types.items():
            if key in kwargs:
                kwargs[key] = get_val_from_param(kwargs[key],
                                                 path_param_definitions)

        # Add body parameters
        if body_name not in arguments:
            logger.debug("Body parameter '%s' not in function arguments", body_name)
        else:
            logger.debug("Body parameter '%s' in function arguments", body_name)
            kwargs[body_name] = request_body

        # Add query parameters
        query_arguments = copy.deepcopy(default_query_params)
        query_arguments.update(flask.request.args.items())
        for key, value in query_arguments.items():
            if key not in arguments:
                logger.debug("Query Parameter '%s' not in function arguments", key)
            else:
                logger.debug("Query Parameter '%s' in function arguments", key)
                try:
                    query_param = query_types[key]
                except KeyError:  # pragma: no cover
                    logger.error("Function argument '{}' not defined in specification".format(key))
                else:
                    logger.debug('%s is a %s', key, query_param)
                    kwargs[key] = get_val_from_param(value, query_param)

        # Add formData parameters
        form_arguments = copy.deepcopy(default_form_params)
        form_arguments.update(flask.request.form.items())
        for key, value in form_arguments.items():
            if key not in arguments:
                logger.debug("FormData parameter '%s' not in function arguments", key)
            else:
                logger.debug("FormData parameter '%s' in function arguments", key)
                try:
                    form_param = form_types[key]
                except KeyError:  # pragma: no cover
                    logger.error("Function argument '{}' not defined in specification".format(key))
                else:
                    kwargs[key] = get_val_from_param(value, form_param)

        # Add file parameters
        file_arguments = flask.request.files
        for key, value in file_arguments.items():
            if key not in arguments:
                logger.debug("File parameter (formData) '%s' not in function arguments", key)
            else:
                logger.debug("File parameter (formData) '%s' in function arguments", key)
                kwargs[key] = value

        return function(*args, **kwargs)

    return wrapper
