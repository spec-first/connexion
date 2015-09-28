import werkzeug.exceptions as exceptions
import flask
import functools
import inspect
import logging
import six

logger = logging.getLogger(__name__)

# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': float,
            'string': str,
            'boolean': bool,
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


def parameter_to_arg(parameters, function):
    """
    Pass query and body parameters as keyword arguments to handler function.

    See (https://github.com/zalando/connexion/issues/59)
    :type body_schema: dict|None
    :type parameters: dict|None
    """
    body_parameters = [parameter for parameter in parameters if parameter['in'] == 'body'] or [{}]
    body_name = body_parameters[0].get('name')
    body_schema = body_parameters[0].get('schema', {})  # type: dict[str, str]
    body_properties = body_schema.get('properties', {})
    body_types = {name: properties['type'] for name, properties in body_properties.items()}  # type: dict[str, str]
    query_types = {parameter['name']: parameter['type']
                   for parameter in parameters if parameter['in'] == 'query'}  # type: dict[str, str]
    arguments = get_function_arguments(function)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        logger.debug('Function Arguments: %s', arguments)

        try:
            body_parameters = flask.request.json or {}
        except exceptions.BadRequest:
            body_parameters = {}

        # Add body parameters
        if isinstance(body_parameters, dict):
            for key, value in body_parameters.items():
                if key not in arguments:
                    logger.debug("Body parameter '%s' not in function arguments", key)
                else:
                    logger.debug("Body parameter '%s' in function arguments", key)
                    key_type = body_types[key]
                    logger.debug('%s is a %s', key, key_type)
                    type_func = TYPE_MAP[key_type]  # convert value to right type
                    kwargs[key] = type_func(value)
        else:
            if body_name not in arguments:
                logger.debug("Body parameter '%s' not in function arguments", body_name)
            else:
                logger.debug("Body parameter '%s' in function arguments", body_name)
                kwargs[body_name] = body_parameters

        # Add query parameters
        for key, value in flask.request.args.items():
            if key not in arguments:
                logger.debug("Query Parameter '%s' not in function arguments", key)
            else:
                logger.debug("Query Parameter '%s' in function arguments", key)
                key_type = query_types[key]
                logger.debug('%s is a %s', key, key_type)
                type_func = TYPE_MAP[key_type]  # convert value to right type
                kwargs[key] = type_func(value)

        return function(*args, **kwargs)

    return wrapper
