import functools
import inspect
import logging
import re

import inflection
import six

from ..http_facts import FORM_CONTENT_TYPES
from ..lifecycle import ConnexionRequest  # NOQA
from ..utils import all_json

try:
    import builtins
except ImportError:  # pragma: no cover
    import __builtin__ as builtins


logger = logging.getLogger(__name__)

# Python 2/3 compatibility:
try:
    py_string = unicode
except NameError:  # pragma: no cover
    py_string = str  # pragma: no cover


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


def parameter_to_arg(operation, function, pythonic_params=False):
    """
    Pass query and body parameters as keyword arguments to handler function.

    See (https://github.com/zalando/connexion/issues/59)
    :param operation: The operation being called
    :type operation: connexion.operations.AbstractOperation
    :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended to
    any shadowed built-ins
    :type pythonic_params: bool
    :type function: function|None
    """
    consumes = operation.consumes

    # swagger2 body
    body_parameters = [p for p in parameters if p['in'] == 'body'] or [{}]
    body_name = sanitize_param(body_parameters[0].get('name'))
    default_body = body_parameters[0].get('schema', {}).get('default')

    form_defns = {sanitize_param(p['name']): p
                  for p in parameters
                  if p['in'] == 'formData'}

    # openapi3 body
    if body_name is None and body_schema is not None:
        logger.debug('body schema is %s', body_schema)
        body_properties = {sanitize_param(k): v
                           for k, v
                           in body_schema.get('properties', {}).items()}
        default_body = body_schema.get('default', default_body)
    else:
        body_properties = {}

    def pythonic(name):
        name = name and snake_and_shadow(name)
        return name and re.sub('^[^a-zA-Z_]+', '', re.sub('[^0-9a-zA-Z_]', '', name))

    def sanitized(name):
        return name and re.sub('^[^a-zA-Z_]+', '', re.sub('[^0-9a-zA-Z_]', '', name))

    sanitize = pythonic if pythonic_params else sanitized
    arguments, has_kwargs = inspect_function_arguments(function)

    @functools.wraps(function)
    def wrapper(request):
        # type: (ConnexionRequest) -> Any
        logger.debug('Function Arguments: %s', arguments)
        kwargs = {}

        logger.error(pythonic_params)
        if all_json(consumes):
            request_body = request.json
            logger.error("json")
        elif consumes[0] in FORM_CONTENT_TYPES:
            request_body = {sanitize(k): v for k, v in request.form.items()}
            logger.error("form")
        else:
            request_body = request.body
            logger.error("raw body")

        logger.error(request_body)
        # accept formData even even if mimetype is wrong for backwards
        # compatability  :/
        request_body = request_body or {sanitize(k): v for k, v in request.form.items()}

        try:
            query = request.query.to_dict(flat=False)
        except AttributeError:
            query = dict(request.query.items())

<<<<<<< HEAD
        if body_schema and body_name is None:
            x_body_name = body_schema.get('x-body-name', 'body')
            logger.debug('x-body-name is %s' % x_body_name)
            if x_body_name in arguments or has_kwargs:
                kwargs[x_body_name] = request_body

        # swagger2 body param and formData
        # Add body parameters
        if body_name:
            if not has_kwargs and body_name not in arguments:
                logger.debug("Body parameter '%s' not in function arguments", body_name)
            else:
                logger.debug("Body parameter '%s' in function arguments", body_name)
                kwargs[body_name] = request_body

        if not body_properties:
            # swagger 2
            # Add formData parameters
            form_arguments = copy.deepcopy(default_form_params)
            form_arguments.update({sanitize_param(k): v for k, v in request.form.items()})
            for key, value in form_arguments.items():
                if not has_kwargs and key not in arguments:
                    logger.debug("FormData parameter '%s' not in function arguments", key)
                else:
                    logger.debug("FormData parameter '%s' in function arguments", key)
                    try:
                        form_defn = form_defns[key]
                    except KeyError:  # pragma: no cover
                        logger.error("Function argument '{}' not defined in specification".format(key))
                    else:
                        kwargs[key] = get_val_from_param(value, form_defn)

        # Add query parameters
        query_arguments = copy.deepcopy(default_query_params)
        query_arguments.update(request.query)
        for key, value in query_arguments.items():
            key = sanitize_param(key)
            if not has_kwargs and key not in arguments:
                logger.debug("Query Parameter '%s' not in function arguments", key)
            else:
                logger.debug("Query Parameter '%s' in function arguments", key)
                try:
                    query_defn = query_defns[key]
                except KeyError:  # pragma: no cover
                    logger.error("Function argument '{}' not defined in specification".format(key))
                else:
                    logger.debug('%s is a %s', key, query_defn)
                    kwargs[key] = get_val_from_param(value, query_defn)

        # Add file parameters
        file_arguments = request.files
        for key, value in file_arguments.items():
            if not has_kwargs and key not in arguments:
                logger.debug("File parameter (formData) '%s' not in function arguments", key)
            else:
                logger.debug("File parameter (formData) '%s' in function arguments", key)
                kwargs[key] = value

        kwargs.update(
            operation.get_arguments(request.path_params, query, request_body,
                                    request.files, arguments, has_kwargs, sanitize)
        )

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
