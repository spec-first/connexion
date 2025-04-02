"""
This module defines URIParsers which parse query and path parameters according to OpenAPI
serialization rules.
"""

import abc
import json
import logging
import re

from starlette.datastructures import UploadFile

from connexion.exceptions import TypeValidationError
from connexion.utils import all_json, coerce_type, deep_merge

logger = logging.getLogger("connexion.decorators.uri_parsing")

QUERY_STRING_DELIMITERS = {
    "spaceDelimited": " ",
    "pipeDelimited": "|",
    "simple": ",",
    "form": ",",
}


class AbstractURIParser(metaclass=abc.ABCMeta):
    parsable_parameters = ["query", "path"]

    def __init__(self, param_defns, body_defn):
        """
        a URI parser is initialized with parameter definitions.
        When called with a request object, it handles array types in the URI
        both in the path and query according to the spec.
        Some examples include:
        - https://mysite.fake/in/path/1,2,3/            # path parameters
        - https://mysite.fake/?in_query=a,b,c           # simple query params
        - https://mysite.fake/?in_query=a|b|c           # various separators
        - https://mysite.fake/?in_query=a&in_query=b,c  # complex query params
        """
        self._param_defns = {
            p["name"]: p for p in param_defns if p["in"] in self.parsable_parameters
        }
        self._body_schema = body_defn.get("schema", {})
        self._body_encoding = body_defn.get("encoding", {})

    @property
    @abc.abstractmethod
    def param_defns(self):
        """
        returns the parameter definitions by name
        """

    @property
    @abc.abstractmethod
    def param_schemas(self):
        """
        returns the parameter schemas by name
        """

    def __repr__(self):
        """
        :rtype: str
        """
        return "<{classname}>".format(
            classname=self.__class__.__name__
        )  # pragma: no cover

    @abc.abstractmethod
    def resolve_form(self, form_data):
        """Resolve cases where form parameters are provided multiple times."""

    @abc.abstractmethod
    def resolve_query(self, query_data):
        """Resolve cases where query parameters are provided multiple times."""

    @abc.abstractmethod
    def resolve_path(self, path):
        """Resolve cases where path parameters include lists"""

    @abc.abstractmethod
    def _resolve_param_duplicates(self, values, param_defn, _in):
        """Resolve cases where query parameters are provided multiple times.
        For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
        `a` could be "4,5,6", or "1,2,3" or "1,2,3,4,5,6" depending on the
        implementation.
        """

    @abc.abstractmethod
    def _split(self, value, param_defn, _in):
        """
        takes a string, a parameter definition, and a parameter type
        and returns an array that has been constructed according to
        the parameter definition.
        """

    def resolve_params(self, params, _in):
        """
        takes a dict of parameters, and resolves the values into
        the correct array type handling duplicate values, and splitting
        based on the collectionFormat defined in the spec.
        """
        resolved_param = {}
        for k, values in params.items():
            param_defn = self.param_defns.get(k)
            param_schema = self.param_schemas.get(k)

            if not (param_defn or param_schema):
                # rely on validation
                resolved_param[k] = values
                continue

            if _in == "path":
                # multiple values in a path is impossible
                values = [values]

            # Handle complex schemas (oneOf, anyOf, allOf) - look for 'type' at root or inside them
            is_array = False
            if param_schema:
                if "type" in param_schema:
                    is_array = param_schema["type"] == "array"
                elif "oneOf" in param_schema:
                    # Try to find an array type in oneOf options
                    for schema in param_schema["oneOf"]:
                        if schema.get("type") == "array":
                            is_array = True
                            break
                elif "anyOf" in param_schema:
                    # Try to find an array type in anyOf options
                    for schema in param_schema["anyOf"]:
                        if schema.get("type") == "array":
                            is_array = True
                            break
                elif "allOf" in param_schema:
                    # Try to find an array type in allOf requirements
                    for schema in param_schema["allOf"]:
                        if schema.get("type") == "array":
                            is_array = True
                            break

            if is_array:
                # resolve variable re-assignment, handle explode
                values = self._resolve_param_duplicates(values, param_defn, _in)
                # handle array styles
                resolved_param[k] = self._split(values, param_defn, _in)
            else:
                resolved_param[k] = values[-1]

            try:
                resolved_param[k] = coerce_type(
                    param_defn, resolved_param[k], "parameter", k
                )
            except TypeValidationError:
                pass

        return resolved_param


class OpenAPIURIParser(AbstractURIParser):
    style_defaults = {
        "path": "simple",
        "header": "simple",
        "query": "form",
        "cookie": "form",
        "form": "form",
    }

    @property
    def param_defns(self):
        return self._param_defns

    @property
    def form_defns(self):
        return {k: v for k, v in self._body_schema.get("properties", {}).items()}

    @property
    def param_schemas(self):
        return {k: v.get("schema", {}) for k, v in self.param_defns.items()}

    def resolve_form(self, form_data):
        if self._body_schema is None or self._body_schema.get("type") != "object":
            return form_data
            
        # Process form data
            
        for k in form_data:
            encoding = self._body_encoding.get(k, {"style": "form"})
            
            # Look for the field definition in properties first
            defn = self.form_defns.get(k, {})
            
            # If not found directly, look for it in complex schemas
            if not defn and "allOf" in self._body_schema:
                for schema in self._body_schema["allOf"]:
                    if "properties" in schema and k in schema["properties"]:
                        defn = schema["properties"][k]
                        break
            
            # Special handling for file uploads in OpenAPI 3.1 with allOf schema
            
            if isinstance(form_data[k], UploadFile):
                # Check if this is an OpenAPI 3.1 schema with allOf and file property
                is_openapi31_allof = (
                    hasattr(self._body_schema, "get") and
                    self._body_schema.get("components", {}) is not None and
                    "allOf" in self._body_schema
                )
                
                has_file_property = False
                if is_openapi31_allof:
                    for schema in self._body_schema.get("allOf", []):
                        if "properties" in schema and k in schema.get("properties", {}):
                            has_file_property = True
                            break
                
                # Skip processing for file uploads in OpenAPI 3.1 with allOf and file property
                if is_openapi31_allof and has_file_property:
                    continue
                
            # Handle arrays in oneOf/anyOf/allOf schemas
            is_array = False
            if "type" in defn and defn["type"] == "array":
                is_array = True
            elif "oneOf" in defn:
                for schema in defn["oneOf"]:
                    if schema.get("type") == "array":
                        is_array = True
                        break
            elif "anyOf" in defn:
                for schema in defn["anyOf"]:
                    if schema.get("type") == "array":
                        is_array = True
                        break
            elif "allOf" in defn:
                for schema in defn["allOf"]:
                    if schema.get("type") == "array":
                        is_array = True
                        break
            
            # TODO support more form encoding styles
            form_data[k] = self._resolve_param_duplicates(
                form_data[k], encoding, "form"
            )
            
            if "contentType" in encoding and all_json([encoding.get("contentType")]):
                form_data[k] = json.loads(form_data[k])
            elif is_array:
                form_data[k] = self._split(form_data[k], encoding, "form")
            
            # If the value is still a list with just one string value, and it's not an array type,
            # extract the single value to avoid the "not of type string" error
            if isinstance(form_data[k], list) and len(form_data[k]) == 1 and not is_array:
                form_data[k] = form_data[k][0]
                
            # Only try to coerce non-UploadFile values for OpenAPI 3.1
            is_openapi31 = hasattr(self._body_schema, "get") and self._body_schema.get("components", {}).get("pathItems", None) is not None
            
            if not isinstance(form_data[k], UploadFile) or not is_openapi31:
                form_data[k] = coerce_type(defn, form_data[k], "requestBody", k)
            
        # Return processed form data
        return form_data

    def _make_deep_object(self, k, v):
        """consumes keys, value pairs like (a[foo][bar], "baz")
        returns (a, {"foo": {"bar": "baz"}}}, is_deep_object)
        """
        root_key = None
        if k in self.param_schemas.keys():
            return k, v, False
        else:
            for key in self.param_schemas.keys():
                if k.startswith(key) and "[" in k:
                    root_key = key.replace(k, "")

        if not root_key:
            root_key = k.split("[", 1)[0]
            if k == root_key:
                return k, v, False

        if not self._is_deep_object_style_param(root_key):
            return k, v, False

        key_path = re.findall(r"\[([^\[\]]*)\]", k)
        root = prev = node = {}
        for k in key_path:
            node[k] = {}
            prev = node
            node = node[k]
        prev[k] = v[0]
        return root_key, [root], True

    def _is_deep_object_style_param(self, param_name):
        default_style = self.style_defaults["query"]
        style = self.param_defns.get(param_name, {}).get("style", default_style)
        return style == "deepObject"

    def _preprocess_deep_objects(self, query_data):
        """deep objects provide a way of rendering nested objects using query
        parameters.
        """
        deep = [self._make_deep_object(k, v) for k, v in query_data.items()]
        root_keys = [k for k, v, is_deep_object in deep]
        ret = dict.fromkeys(root_keys, [{}])
        for k, v, is_deep_object in deep:
            if is_deep_object:
                ret[k] = [deep_merge(v[0], ret[k][0])]
            else:
                ret[k] = v
        return ret

    def resolve_query(self, query_data):
        query_data = self._preprocess_deep_objects(query_data)
        return self.resolve_params(query_data, "query")

    def resolve_path(self, path_data):
        return self.resolve_params(path_data, "path")

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """Resolve cases where query parameters are provided multiple times.
        The default behavior is to use the first-defined value.
        For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
        `a` would be "4,5,6".
        However, if 'explode' is 'True' then the duplicate values
        are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        # Special case for UploadFile objects in the list - don't try to join them
        
        # If values is a single UploadFile, return it directly
        if isinstance(values, UploadFile):
            return values
            
        # If it's a list containing UploadFile objects, we need to return the list as is
        if hasattr(values, '__iter__') and not isinstance(values, (str, bytes)):
            if any(isinstance(v, UploadFile) for v in values):
                return values
            
        # Normal parameter handling
        default_style = OpenAPIURIParser.style_defaults[_in]
        style = param_defn.get("style", default_style)
        delimiter = QUERY_STRING_DELIMITERS.get(style, ",")
        is_form = style == "form"
        explode = param_defn.get("explode", is_form)
        
        if explode:
            # Make sure values is iterable before joining
            if hasattr(values, '__iter__') and not isinstance(values, (str, bytes)):
                # Filter out any UploadFile objects before joining
                str_values = [v for v in values if not isinstance(v, UploadFile)]
                if str_values:
                    return delimiter.join(str_values)
                return values
            return values

        # default to last defined value
        if hasattr(values, '__getitem__') and not isinstance(values, (str, bytes)):
            return values[-1]
        return values

    @staticmethod
    def _split(value, param_defn, _in):
        # Special case for UploadFile objects - don't try to split them
        if isinstance(value, UploadFile):
            return value
            
        default_style = OpenAPIURIParser.style_defaults[_in]
        style = param_defn.get("style", default_style)
        delimiter = QUERY_STRING_DELIMITERS.get(style, ",")
        
        # Make sure value has a split method
        if hasattr(value, 'split'):
            return value.split(delimiter)
        return value


class Swagger2URIParser(AbstractURIParser):
    """
    Adheres to the Swagger2 spec,
    Assumes that the last defined query parameter should be used.
    """

    parsable_parameters = ["query", "path", "formData"]

    @property
    def param_defns(self):
        return self._param_defns

    @property
    def param_schemas(self):
        return self._param_defns  # swagger2 conflates defn and schema

    def resolve_form(self, form_data):
        return self.resolve_params(form_data, "form")

    def resolve_query(self, query_data):
        return self.resolve_params(query_data, "query")

    def resolve_path(self, path_data):
        return self.resolve_params(path_data, "path")

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """Resolve cases where query parameters are provided multiple times.
        The default behavior is to use the first-defined value.
        For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
        `a` would be "4,5,6".
        However, if 'collectionFormat' is 'multi' then the duplicate values
        are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get("collectionFormat") == "multi":
            return ",".join(values)
        # default to last defined value
        return values[-1]

    @staticmethod
    def _split(value, param_defn, _in):
        if param_defn.get("collectionFormat") == "pipes":
            return value.split("|")
        return value.split(",")


class FirstValueURIParser(Swagger2URIParser):
    """
    Adheres to the Swagger2 spec
    Assumes that the first defined query parameter should be used
    """

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """Resolve cases where query parameters are provided multiple times.
        The default behavior is to use the first-defined value.
        For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
        `a` would be "1,2,3".
        However, if 'collectionFormat' is 'multi' then the duplicate values
        are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get("collectionFormat") == "multi":
            return ",".join(values)
        # default to first defined value
        return values[0]


class AlwaysMultiURIParser(Swagger2URIParser):
    """
    Does not adhere to the Swagger2 spec, but is backwards compatible with
    connexion behavior in version 1.4.2
    """

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """Resolve cases where query parameters are provided multiple times.
        The default behavior is to join all provided parameters together.
        For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
        `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get("collectionFormat") == "pipes":
            return "|".join(values)
        return ",".join(values)
