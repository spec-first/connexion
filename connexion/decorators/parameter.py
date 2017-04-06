import copy
import functools
import inspect
import logging
import re

import inflection
import six

from ..lifecycle import ConnexionRequest  # NOQA
from ..utils import all_json, boolean, is_null, is_nullable

try:
    import builtins
except ImportError:
    import __builtin__ as builtins


logger = logging.getLogger(__name__)

# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': float,
            'string': str,
            'boolean': boolean,
            'array': list,
            'object': dict}  # map of swagger types to python types


def inspect_function_arguments(function):  # pragma: no cover
    """
    Returns the list of variables names of a function and if it
    accepts keyword arguments.

    :type function: Callable
    :rtype: tuple[list[str], bool]
    """
    if six.PY3:
        parameters = inspect.signature(function).parameters
        bound_arguments = [name for name, p in parameters.items()
                           if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
        has_kwargs = any(p.kind == p.VAR_KEYWORD for p in parameters.values())
        return list(bound_arguments), has_kwargs
    else:
        argspec = inspect.getargspec(function)
        return argspec.args, bool(argspec.keywords)


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


def snake_and_shadow(name):
    """
    Converts the given name into Pythonic form. Firstly it converts CamelCase names to snake_case. Secondly it looks to
    see if the name matches a known built-in and if it does it appends an underscore to the name.
    :param name: The parameter name
    :type name: str
    :return:
    """
    snake = inflection.underscore(name)
    if snake in builtins.__dict__.keys():
        return "{}_".format(snake)
    return snake


def parameter_to_arg(parameters, consumes, function, pythonic_params=False):
    """
    Pass query and body parameters as keyword arguments to handler function.

    See (https://github.com/zalando/connexion/issues/59)
    :param parameters: All the parameters of the handler functions
    :type parameters: dict|None
    :param consumes: The list of content types the operation consumes
    :type consumes: list
    :param function: The handler function for the REST endpoint.
    :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended to
    any shadowed built-ins
    :type pythonic_params: bool
    :type function: function|None
    """
    def sanitize_param(name):
        if name and pythonic_params:
            name = snake_and_shadow(name)
        return name and re.sub('^[^a-zA-Z_]+', '', re.sub('[^0-9a-zA-Z_]', '', name))

    body_parameters = [parameter for parameter in parameters if parameter['in'] == 'body'] or [{}]
    body_name = sanitize_param(body_parameters[0].get('name'))
    default_body = body_parameters[0].get('schema', {}).get('default')
    query_types = {sanitize_param(parameter['name']): parameter
                   for parameter in parameters if parameter['in'] == 'query'}  # type: dict[str, str]
    form_types = {sanitize_param(parameter['name']): parameter
                  for parameter in parameters if parameter['in'] == 'formData'}
    path_types = {parameter['name']: parameter
                  for parameter in parameters if parameter['in'] == 'path'}
    arguments, has_kwargs = inspect_function_arguments(function)
    default_query_params = {sanitize_param(param['name']): param['default']
                            for param in parameters if param['in'] == 'query' and 'default' in param}
    default_form_params = {sanitize_param(param['name']): param['default']
                           for param in parameters if param['in'] == 'formData' and 'default' in param}

    @functools.wraps(function)
    def wrapper(request):
        # type: (ConnexionRequest) -> Any
        logger.debug('Function Arguments: %s', arguments)
        kwargs = {}

        if all_json(consumes):
            request_body = request.json
        else:
            request_body = request.body

        if default_body and not request_body:
            request_body = default_body

        # Parse path parameters
        path_params = request.path_params
        for key, path_param_definitions in path_types.items():
            if key in path_params:
                kwargs[key] = get_val_from_param(path_params[key],
                                                 path_param_definitions)

        # Add body parameters
        if not has_kwargs and body_name not in arguments:
            logger.debug("Body parameter '%s' not in function arguments", body_name)
        elif body_name:
            logger.debug("Body parameter '%s' in function arguments", body_name)
            kwargs[body_name] = request_body

        # Add query parameters
        query_arguments = copy.deepcopy(default_query_params)
        query_arguments.update({sanitize_param(k): v for k, v in request.query.items()})
        for key, value in query_arguments.items():
            if not has_kwargs and key not in arguments:
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
        form_arguments.update({sanitize_param(k): v for k, v in request.form.items()})
        for key, value in form_arguments.items():
            if not has_kwargs and key not in arguments:
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
        file_arguments = request.files
        for key, value in file_arguments.items():
            if not has_kwargs and key not in arguments:
                logger.debug("File parameter (formData) '%s' not in function arguments", key)
            else:
                logger.debug("File parameter (formData) '%s' in function arguments", key)
                kwargs[key] = value

        # optionally convert parameter variable names to un-shadowed, snake_case form
        if pythonic_params:
            kwargs = {snake_and_shadow(k): v for k, v in kwargs.items()}

        # add context info (e.g. from security decorator)
        for key, value in request.context.items():
            if has_kwargs or key in arguments:
                kwargs[key] = value
            else:
                logger.debug("Context parameter '%s' not in function arguments", key)
        return function(**kwargs)

    return wrapper
