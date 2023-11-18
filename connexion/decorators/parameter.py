"""
This module defines a decorator to convert request parameters to arguments for the view function.
"""
import abc
import asyncio
import builtins
import functools
import keyword
import logging
import re
import typing as t
from copy import copy, deepcopy

import inflection

from connexion.context import context, operation
from connexion.frameworks.abstract import Framework
from connexion.http_facts import FORM_CONTENT_TYPES
from connexion.lifecycle import ConnexionRequest, WSGIRequest
from connexion.operations import AbstractOperation, Swagger2Operation
from connexion.utils import (
    deep_merge,
    inspect_function_arguments,
    is_null,
    is_nullable,
    make_type,
)

logger = logging.getLogger(__name__)

CONTEXT_NAME = "context_"


class BaseParameterDecorator:
    def __init__(
        self,
        *,
        framework: t.Type[Framework],
        pythonic_params: bool = False,
    ) -> None:
        self.framework = framework
        self.sanitize_fn = pythonic if pythonic_params else sanitized

    def _maybe_get_body(
        self,
        request: t.Union[WSGIRequest, ConnexionRequest],
        *,
        arguments: t.List[str],
        has_kwargs: bool,
    ) -> t.Any:
        body_name = self.sanitize_fn(operation.body_name(request.content_type))
        # Pass form contents separately for Swagger2 for backward compatibility with
        # Connexion 2 Checking for body_name is not enough
        if (body_name in arguments or has_kwargs) or (
            request.mimetype in FORM_CONTENT_TYPES
            and isinstance(operation, Swagger2Operation)
        ):
            return request.get_body()
        else:
            return None

    @abc.abstractmethod
    def __call__(self, function: t.Callable) -> t.Callable:
        raise NotImplementedError


class SyncParameterDecorator(BaseParameterDecorator):
    def __call__(self, function: t.Callable) -> t.Callable:
        unwrapped_function = unwrap_decorators(function)
        arguments, has_kwargs = inspect_function_arguments(unwrapped_function)

        @functools.wraps(function)
        def wrapper(request: WSGIRequest) -> t.Any:
            request_body = self._maybe_get_body(
                request, arguments=arguments, has_kwargs=has_kwargs
            )

            kwargs = prep_kwargs(
                request,
                request_body=request_body,
                files=request.files(),
                arguments=arguments,
                has_kwargs=has_kwargs,
                sanitize=self.sanitize_fn,
            )

            return function(**kwargs)

        return wrapper


class AsyncParameterDecorator(BaseParameterDecorator):
    def __call__(self, function: t.Callable) -> t.Callable:
        unwrapped_function = unwrap_decorators(function)
        arguments, has_kwargs = inspect_function_arguments(unwrapped_function)

        @functools.wraps(function)
        async def wrapper(request: ConnexionRequest) -> t.Any:
            request_body = self._maybe_get_body(
                request, arguments=arguments, has_kwargs=has_kwargs
            )

            while asyncio.iscoroutine(request_body):
                request_body = await request_body

            kwargs = prep_kwargs(
                request,
                request_body=request_body,
                files=await request.files(),
                arguments=arguments,
                has_kwargs=has_kwargs,
                sanitize=self.sanitize_fn,
            )

            return await function(**kwargs)

        return wrapper


def prep_kwargs(
    request: t.Union[WSGIRequest, ConnexionRequest],
    *,
    request_body: t.Any,
    files: t.Dict[str, t.Any],
    arguments: t.List[str],
    has_kwargs: bool,
    sanitize: t.Callable,
) -> dict:
    kwargs = get_arguments(
        operation,
        path_params=request.path_params,
        query_params=request.query_params,
        body=request_body,
        files=files,
        arguments=arguments,
        has_kwargs=has_kwargs,
        sanitize=sanitize,
        content_type=request.mimetype,
    )

    # optionally convert parameter variable names to un-shadowed, snake_case form
    kwargs = {sanitize(k): v for k, v in kwargs.items()}

    # add context info (e.g. from security decorator)
    for key, value in context.items():
        if has_kwargs or key in arguments:
            kwargs[key] = value
        else:
            logger.debug("Context parameter '%s' not in function arguments", key)
    # attempt to provide the request context to the function
    if CONTEXT_NAME in arguments:
        kwargs[CONTEXT_NAME] = context

    return kwargs


def unwrap_decorators(function: t.Callable) -> t.Callable:
    """Unwrap decorators to return the original function."""
    while hasattr(function, "__wrapped__"):
        function = function.__wrapped__  # type: ignore
    return function


def snake_and_shadow(name: str) -> str:
    """
    Converts the given name into Pythonic form. Firstly it converts CamelCase names to snake_case. Secondly it looks to
    see if the name matches a known built-in and if it does it appends an underscore to the name.
    :param name: The parameter name
    """
    snake = inflection.underscore(name)
    if snake in builtins.__dict__ or keyword.iskeyword(snake):
        return f"{snake}_"
    return snake


def sanitized(name: str) -> str:
    return name and re.sub(
        "^[^a-zA-Z_]+", "", re.sub("[^0-9a-zA-Z_]", "", re.sub(r"\[(?!])", "_", name))
    )


def pythonic(name: str) -> str:
    name = name and snake_and_shadow(name)
    return sanitized(name)


def get_arguments(
    operation: AbstractOperation,
    *,
    path_params: dict,
    query_params: dict,
    body: t.Any,
    files: dict,
    arguments: t.List[str],
    has_kwargs: bool,
    sanitize: t.Callable,
    content_type: str,
) -> t.Dict[str, t.Any]:
    """
    get arguments for handler function
    """
    ret = {}
    ret.update(_get_path_arguments(path_params, operation=operation, sanitize=sanitize))
    ret.update(
        _get_query_arguments(
            query_params,
            operation=operation,
            arguments=arguments,
            has_kwargs=has_kwargs,
            sanitize=sanitize,
        )
    )

    if operation.method.upper() == "TRACE":
        # TRACE requests MUST NOT include a body (RFC7231 section 4.3.8)
        return ret

    ret.update(
        _get_body_argument(
            body,
            operation=operation,
            arguments=arguments,
            has_kwargs=has_kwargs,
            sanitize=sanitize,
            content_type=content_type,
        )
    )
    body_schema = operation.body_schema(content_type)
    ret.update(_get_file_arguments(files, arguments, body_schema, has_kwargs))
    return ret


def _get_path_arguments(
    path_params: dict, *, operation: AbstractOperation, sanitize: t.Callable
) -> dict:
    """
    Extract handler function arguments from path parameters
    """
    kwargs = {}

    path_definitions = {
        parameter["name"]: parameter
        for parameter in operation.parameters
        if parameter["in"] == "path"
    }

    for name, value in path_params.items():
        sanitized_key = sanitize(name)
        if name in path_definitions:
            kwargs[sanitized_key] = _get_val_from_param(value, path_definitions[name])
        else:  # Assume path params mechanism used for injection
            kwargs[sanitized_key] = value
    return kwargs


def _get_val_from_param(value: t.Any, param_definitions: t.Dict[str, dict]) -> t.Any:
    """Cast a value according to its definition in the specification."""
    param_schema = param_definitions.get("schema", param_definitions)

    if is_nullable(param_schema) and is_null(value):
        return None

    if param_schema["type"] == "array":
        type_ = param_schema["items"]["type"]
        format_ = param_schema["items"].get("format")
        return [make_type(part, type_, format_) for part in value]
    else:
        type_ = param_schema["type"]
        format_ = param_schema.get("format")
        return make_type(value, type_, format_)


def _get_query_arguments(
    query_params: dict,
    *,
    operation: AbstractOperation,
    arguments: t.List[str],
    has_kwargs: bool,
    sanitize: t.Callable,
) -> dict:
    """
    extract handler function arguments from the query parameters
    """
    query_definitions = {
        parameter["name"]: parameter
        for parameter in operation.parameters
        if parameter["in"] == "query"
    }

    default_query_params = _get_query_defaults(query_definitions)

    query_arguments = deepcopy(default_query_params)
    query_arguments = deep_merge(query_arguments, query_params)
    return _query_args_helper(
        query_definitions, query_arguments, arguments, has_kwargs, sanitize
    )


def _get_query_defaults(query_definitions: t.Dict[str, dict]) -> t.Dict[str, t.Any]:
    """Get the default values for the query parameter from the parameter definition."""
    defaults = {}
    for k, v in query_definitions.items():
        try:
            if "default" in v:
                defaults[k] = v["default"]
            elif v["schema"]["type"] == "object":
                defaults[k] = _get_default_obj(v["schema"])
            else:
                defaults[k] = v["schema"]["default"]
        except KeyError:
            pass
    return defaults


def _get_default_obj(schema: dict) -> dict:
    try:
        return deepcopy(schema["default"])
    except KeyError:
        properties = schema.get("properties", {})
        return _build_default_obj_recursive(properties, {})


def _build_default_obj_recursive(properties: dict, default_object: dict) -> dict:
    """takes disparate and nested default keys, and builds up a default object"""
    for name, property_ in properties.items():
        if "default" in property_ and name not in default_object:
            default_object[name] = copy(property_["default"])
        elif property_.get("type") == "object" and "properties" in property_:
            default_object.setdefault(name, {})
            default_object[name] = _build_default_obj_recursive(
                property_["properties"], default_object[name]
            )
    return default_object


def _query_args_helper(
    query_definitions: dict,
    query_arguments: dict,
    function_arguments: t.List[str],
    has_kwargs: bool,
    sanitize: t.Callable,
) -> dict:
    result = {}
    for key, value in query_arguments.items():
        sanitized_key = sanitize(key)
        if not has_kwargs and sanitized_key not in function_arguments:
            logger.debug(
                "Query Parameter '%s' (sanitized: '%s') not in function arguments",
                key,
                sanitized_key,
            )
        else:
            logger.debug(
                "Query Parameter '%s' (sanitized: '%s') in function arguments",
                key,
                sanitized_key,
            )
            try:
                query_defn = query_definitions[key]
            except KeyError:  # pragma: no cover
                logger.error(
                    "Function argument '%s' (non-sanitized: %s) not defined in specification",
                    sanitized_key,
                    key,
                )
            else:
                logger.debug("%s is a %s", key, query_defn)
                result.update({sanitized_key: _get_val_from_param(value, query_defn)})
    return result


def _get_body_argument(
    body: t.Any,
    *,
    operation: AbstractOperation,
    arguments: t.List[str],
    has_kwargs: bool,
    sanitize: t.Callable,
    content_type: str,
) -> dict:
    if len(arguments) <= 0 and not has_kwargs:
        return {}

    if not operation.is_request_body_defined:
        return {}

    body_name = sanitize(operation.body_name(content_type))

    if content_type in FORM_CONTENT_TYPES:
        result = _get_body_argument_form(
            body, operation=operation, content_type=content_type
        )

        # Unpack form values for Swagger for compatibility with Connexion 2 behavior
        if content_type in FORM_CONTENT_TYPES and isinstance(
            operation, Swagger2Operation
        ):
            if has_kwargs:
                return result
            else:
                return {
                    sanitize(name): value
                    for name, value in result.items()
                    if sanitize(name) in arguments
                }
    else:
        result = _get_body_argument_json(
            body, operation=operation, content_type=content_type
        )

    if body_name in arguments or has_kwargs:
        return {body_name: result}

    return {}


def _get_body_argument_json(
    body: t.Any, *, operation: AbstractOperation, content_type: str
) -> t.Any:
    # if the body came in null, and the schema says it can be null, we decide
    # to include no value for the body argument, rather than the default body
    if is_nullable(operation.body_schema(content_type)) and is_null(body):
        return None

    if body is None:
        default_body = operation.body_schema(content_type).get("default", {})
        return deepcopy(default_body)

    return body


def _get_body_argument_form(
    body: dict, *, operation: AbstractOperation, content_type: str
) -> dict:
    # now determine the actual value for the body (whether it came in or is default)
    default_body = operation.body_schema(content_type).get("default", {})
    body_props = {
        k: {"schema": v}
        for k, v in operation.body_schema(content_type).get("properties", {}).items()
    }

    # by OpenAPI specification `additionalProperties` defaults to `true`
    # see: https://github.com/OAI/OpenAPI-Specification/blame/3.0.2/versions/3.0.2.md#L2305
    additional_props = operation.body_schema().get("additionalProperties", True)

    body_arg = deepcopy(default_body)
    body_arg.update(body or {})

    if body_props or additional_props:
        return _get_typed_body_values(body_arg, body_props, additional_props)

    return {}


def _get_typed_body_values(body_arg, body_props, additional_props):
    """
    Return a copy of the provided body_arg dictionary
    whose values will have the appropriate types
    as defined in the provided schemas.

    :type body_arg: type dict
    :type body_props: dict
    :type additional_props: dict|bool
    :rtype: dict
    """
    additional_props_defn = (
        {"schema": additional_props} if isinstance(additional_props, dict) else None
    )
    res = {}

    for key, value in body_arg.items():
        try:
            prop_defn = body_props[key]
            res[key] = _get_val_from_param(value, prop_defn)
        except KeyError:  # pragma: no cover
            if not additional_props:
                logger.error(f"Body property '{key}' not defined in body schema")
                continue
            if additional_props_defn is not None:
                value = _get_val_from_param(value, additional_props_defn)
            res[key] = value

    return res


def _get_file_arguments(files, arguments, body_schema: dict, has_kwargs=False):
    results = {}
    for k, v in files.items():
        if not (k in arguments or has_kwargs):
            continue
        if body_schema.get("properties", {}).get(k, {}).get("type") != "array":
            v = v[0]
        results[k] = v

    return results
