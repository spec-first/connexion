"""
This module provides general utility functions used within Connexion.
"""

import asyncio
import functools
import importlib
import inspect
import os
import pkgutil
import sys
import typing as t

import yaml
from starlette.routing import compile_path

from connexion.exceptions import TypeValidationError

if t.TYPE_CHECKING:
    from connexion.middleware.main import API


def boolean(s):
    """
    Convert JSON/Swagger boolean value to Python, raise ValueError otherwise

    >>> boolean('true')
    True

    >>> boolean('false')
    False
    """
    if isinstance(s, bool):
        return s
    elif not hasattr(s, "lower"):
        raise ValueError("Invalid boolean value")
    elif s.lower() == "true":
        return True
    elif s.lower() == "false":
        return False
    else:
        raise ValueError("Invalid boolean value")


# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP: t.Dict[str, t.Any] = {
    "integer": int,
    "number": float,
    "string": str,
    "boolean": boolean,
    "array": list,
    "object": dict,
    "file": lambda x: x,  # Don't cast files
}  # map of swagger types to python types


def make_type(value: t.Any, type_: str, format_: t.Optional[str]) -> t.Any:
    """Cast a value to the type defined in the specification."""
    # In OpenAPI, files are represented with string type and binary format
    if type_ == "string" and format_ == "binary":
        type_ = "file"

    type_func = TYPE_MAP[type_]
    return type_func(value)


def deep_merge(a, b):
    """merges b into a
    in case of conflict the value from b is used
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deep_merge(a[key], b[key])
            elif a[key] == b[key]:
                pass
            else:
                # b overwrites a
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def deep_getattr(obj, attr):
    """
    Recurses through an attribute chain to get the ultimate value.
    """

    attrs = attr.split(".")

    return functools.reduce(getattr, attrs, obj)


def deep_get(obj, keys):
    """
    Recurses through a nested object get a leaf value.

    There are cases where the use of inheritance or polymorphism-- the use of allOf or
    oneOf keywords-- will cause the obj to be a list. In this case the keys will
    contain one or more strings containing integers.

    :type obj: list or dict
    :type keys: list of strings
    """
    if not keys:
        return obj

    if isinstance(obj, list):
        return deep_get(obj[int(keys[0])], keys[1:])
    else:
        return deep_get(obj[keys[0]], keys[1:])


def get_function_from_name(function_name):
    """
    Tries to get function by fully qualified name (e.g. "mymodule.myobj.myfunc")

    :type function_name: str
    """
    if function_name is None:
        raise ValueError("Empty function name")

    if "." in function_name:
        module_name, attr_path = function_name.rsplit(".", 1)
    else:
        module_name = ""
        attr_path = function_name

    module = None
    last_import_error = None

    while not module:
        try:
            module = importlib.import_module(module_name)
        except ImportError as import_error:
            last_import_error = import_error
            if "." in module_name:
                module_name, attr_path1 = module_name.rsplit(".", 1)
                attr_path = f"{attr_path1}.{attr_path}"
            else:
                raise
    try:
        function = deep_getattr(module, attr_path)
    except AttributeError:
        if last_import_error:
            raise last_import_error
        else:
            raise
    return function


def is_json_mimetype(mimetype):
    """
    :type mimetype: str
    :rtype: bool
    """
    if mimetype is None:
        return False

    maintype, subtype = mimetype.split("/")  # type: str, str
    if ";" in subtype:
        subtype, parameter = subtype.split(";", maxsplit=1)
    return maintype == "application" and (
        subtype == "json" or subtype.endswith("+json")
    )


def all_json(mimetypes):
    """
    Returns True if all mimetypes are serialized with json

    :type mimetypes: list
    :rtype: bool

    >>> all_json(['application/json'])
    True
    >>> all_json(['application/x.custom+json'])
    True
    >>> all_json([])
    True
    >>> all_json(['application/xml'])
    False
    >>> all_json(['text/json'])
    False
    >>> all_json(['application/json', 'other/type'])
    False
    >>> all_json(['application/json', 'application/x.custom+json'])
    True
    """
    return all(is_json_mimetype(mimetype) for mimetype in mimetypes)


def is_nullable(param_def):
    return param_def.get("schema", param_def).get("nullable", False) or param_def.get(
        "x-nullable", False
    )  # swagger2


def is_null(value):
    if hasattr(value, "strip") and value.strip() in ["null", "None"]:
        return True

    if value is None:
        return True

    return False


def has_coroutine(function, api=None):
    """
    Checks if function is a coroutine.
    If ``function`` is a decorator (has a ``__wrapped__`` attribute)
    this function will also look at the wrapped function.
    """

    def iscorofunc(func):
        iscorofunc = asyncio.iscoroutinefunction(func)
        while not iscorofunc and hasattr(func, "__wrapped__"):
            func = func.__wrapped__
            iscorofunc = asyncio.iscoroutinefunction(func)
        return iscorofunc

    if api is None:
        return iscorofunc(function)

    else:
        return any(iscorofunc(func) for func in (function, api.get_response))


def yamldumper(openapi):
    """
    Returns a nicely-formatted yaml spec.
    :param openapi: a spec dictionary.
    :return: a nicely-formatted, serialized yaml spec.
    """

    def should_use_block(value):
        char_list = (
            "\u000a"  # line feed
            "\u000d"  # carriage return
            "\u001c"  # file separator
            "\u001d"  # group separator
            "\u001e"  # record separator
            "\u0085"  # next line
            "\u2028"  # line separator
            "\u2029"  # paragraph separator
        )
        for c in char_list:
            if c in value:
                return True
        return False

    def my_represent_scalar(self, tag, value, style=None):
        if should_use_block(value):
            style = "|"
        else:
            style = self.default_style

        node = yaml.representer.ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node

    class NoAnchorDumper(yaml.dumper.SafeDumper):
        """A yaml Dumper that does not replace duplicate entries
        with yaml anchors.
        """

        def ignore_aliases(self, *args):
            return True

    # Dump long lines as "|".
    yaml.representer.SafeRepresenter.represent_scalar = my_represent_scalar

    return yaml.dump(openapi, allow_unicode=True, Dumper=NoAnchorDumper)


def not_installed_error(exc, *, msg=None):  # pragma: no cover
    """Raises the ImportError when the module/object is actually called with a custom message."""

    def _delayed_error(*args, **kwargs):
        if msg is not None:
            raise type(exc)(msg).with_traceback(exc.__traceback__)
        raise exc

    return _delayed_error


def extract_content_type(
    headers: t.Union[t.List[t.Tuple[bytes, bytes]], t.Dict[str, str]]
) -> t.Optional[str]:
    """Extract the mime type and encoding from the content type headers.

    :param headers: Headers from ASGI scope

    :return: The content type if available in headers, otherwise None
    """
    content_type: t.Optional[str] = None

    header_pairs_type = t.Collection[t.Tuple[t.Union[str, bytes], t.Union[str, bytes]]]
    header_pairs: header_pairs_type = headers.items() if isinstance(headers, dict) else headers  # type: ignore
    for key, value in header_pairs:
        # Headers can always be decoded using latin-1:
        # https://stackoverflow.com/a/27357138/4098821
        if isinstance(key, bytes):
            decoded_key: str = key.decode("latin-1")
        else:
            decoded_key = key

        if decoded_key.lower() == "content-type":
            if isinstance(value, bytes):
                content_type = value.decode("latin-1")
            else:
                content_type = value
            break

    return content_type


def split_content_type(
    content_type: t.Optional[str],
) -> t.Tuple[t.Optional[str], t.Optional[str]]:
    """Split the content type in mime_type and encoding. Other parameters are ignored."""
    mime_type, encoding = None, None

    if content_type is None:
        return mime_type, encoding

    # Check for parameters
    if ";" in content_type:
        mime_type, parameters = content_type.split(";", maxsplit=1)

        # Find parameter describing the charset
        prefix = "charset="
        for parameter in parameters.split(";"):
            if parameter.startswith(prefix):
                encoding = parameter[len(prefix) :]
    else:
        mime_type = content_type
    return mime_type, encoding


def coerce_type(param, value, parameter_type, parameter_name=None):
    # TODO: clean up
    TYPE_MAP = {"integer": int, "number": float, "boolean": boolean, "object": dict}

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


def get_root_path(import_name: str) -> str:
    """Copied from Flask:
    https://github.com/pallets/flask/blob/836866dc19218832cf02f8b04911060ac92bfc0b/src/flask/helpers.py#L595

    Find the root path of a package, or the path that contains a
    module. If it cannot be found, returns the current working
    directory.
    """
    # Module already imported and has a file attribute. Use that first.
    mod = sys.modules.get(import_name)

    if mod is not None and hasattr(mod, "__file__") and mod.__file__ is not None:
        return os.path.dirname(os.path.abspath(mod.__file__))

    # Next attempt: check the loader.
    loader = pkgutil.get_loader(import_name)

    # Loader does not exist or we're referring to an unloaded main
    # module or a main module without path (interactive sessions), go
    # with the current working directory.
    if loader is None or import_name == "__main__":
        return os.getcwd()

    if hasattr(loader, "get_filename"):
        filepath = loader.get_filename(import_name)  # type: ignore
    else:
        # Fall back to imports.
        __import__(import_name)
        mod = sys.modules[import_name]
        filepath = getattr(mod, "__file__", None)

        # If we don't have a file path it might be because it is a
        # namespace package. In this case pick the root path from the
        # first module that is contained in the package.
        if filepath is None:
            raise RuntimeError(
                "No root path can be found for the provided module"
                f" {import_name!r}. This can happen because the module"
                " came from an import hook that does not provide file"
                " name information or because it's a namespace package."
                " In this case the root path needs to be explicitly"
                " provided."
            )

    # filepath is import_name.py for a module, or __init__.py for a package.
    return os.path.dirname(os.path.abspath(filepath))


def inspect_function_arguments(function: t.Callable) -> t.Tuple[t.List[str], bool]:
    """
    Returns the list of variables names of a function and if it
    accepts keyword arguments.
    """
    parameters = inspect.signature(function).parameters
    bound_arguments = [
        name
        for name, p in parameters.items()
        if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
    ]
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in parameters.values())
    return list(bound_arguments), has_kwargs


T = t.TypeVar("T")


@t.overload
def sort_routes(routes: t.List[str], *, key: None = None) -> t.List[str]:
    ...


@t.overload
def sort_routes(routes: t.List[T], *, key: t.Callable[[T], str]) -> t.List[T]:
    ...


def sort_routes(routes, *, key=None):
    """Sorts a list of routes from most specific to least specific.

    See Starlette routing documentation and implementation as this function
    is aimed to sort according to that logic.
    - https://www.starlette.io/routing/#route-priority

    The only difference is that a `path` component is appended to each route
    such that `/` is less specific than `/basepath` while they are technically
    not comparable.
    This is because it is also done by the `Mount` class internally:
    https://github.com/encode/starlette/blob/1c1043ca0ab7126419948b27f9d0a78270fd74e6/starlette/routing.py#L388

    For example, from most to least specific:
    - /users/me
    - /users/{username}/projects/{project}
    - /users/{username}

    :param routes: List of routes to sort
    :param key: Function to extract the path from a route if it is not a string

    :return: List of routes sorted from most specific to least specific
    """

    class SortableRoute:
        def __init__(self, path: str) -> None:
            self.path = path.rstrip("/")
            if not self.path.endswith("/{path:path}"):
                self.path += "/{path:path}"
            self.path_regex, _, _ = compile_path(self.path)

        def __lt__(self, other: "SortableRoute") -> bool:
            return bool(other.path_regex.match(self.path))

    return sorted(routes, key=lambda r: SortableRoute(key(r) if key else r))


def sort_apis_by_basepath(apis: t.List["API"]) -> t.List["API"]:
    """Sorts a list of APIs by basepath.

    :param apis: List of APIs to sort

    :return: List of APIs sorted by basepath
    """
    return sort_routes(apis, key=lambda api: api.base_path or "/")
