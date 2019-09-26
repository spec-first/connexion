# Decorators to split query and path parameters
import abc
import functools
import logging
import re

import six

from ..utils import create_empty_dict_from_list
from .decorator import BaseDecorator

logger = logging.getLogger('connexion.decorators.uri_parsing')

QUERY_STRING_DELIMITERS = {
    'spaceDelimited': ' ',
    'pipeDelimited': '|',
    'simple': ',',
    'form': ','
}


@six.add_metaclass(abc.ABCMeta)
class AbstractURIParser(BaseDecorator):
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
        self._param_defns = {p["name"]: p
                             for p in param_defns
                             if p["in"] in self.parsable_parameters}
        self._body_schema = body_defn.get("schema", {})
        self._body_encoding = body_defn.get("encoding", {})

    @abc.abstractproperty
    def param_defns(self):
        """
        returns the parameter definitions by name
        """

    @abc.abstractproperty
    def param_schemas(self):
        """
        returns the parameter schemas by name
        """

    def __repr__(self):
        """
        :rtype: str
        """
        return "<{classname}>".format(
            classname=self.__class__.__name__)  # pragma: no cover

    @abc.abstractmethod
    def resolve_form(self, form_data):
        """ Resolve cases where form parameters are provided multiple times.
        """

    @abc.abstractmethod
    def resolve_query(self, query_data):
        """ Resolve cases where query parameters are provided multiple times.
        """

    @abc.abstractmethod
    def resolve_path(self, path):
        """ Resolve cases where path parameters include lists
        """

    @abc.abstractmethod
    def _resolve_param_duplicates(self, values, param_defn, _in):
        """ Resolve cases where query parameters are provided multiple times.
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
            # extract the dict keys if specified with style: deepObject and explode: true
            # according to https://swagger.io/docs/specification/serialization/#query
            dict_keys = re.findall(r'\[(\w+)\]', k)
            if dict_keys:
                k = k.split("[", 1)[0]
                param_defn = self.param_defns.get(k)
                if param_defn and param_defn.get('style', None) == 'deepObject' and param_defn.get('explode', False):
                    param_schema = self.param_schemas.get(k)
                    if isinstance(values, list) and len(values) == 1 and param_schema['type'] != 'array':
                        values = values[0]
                    resolved_param.setdefault(k, {})
                    resolved_param[k].update(create_empty_dict_from_list(dict_keys, {}, values))
                    continue

            param_defn = self.param_defns.get(k)
            param_schema = self.param_schemas.get(k)

            if not (param_defn or param_schema):
                # rely on validation
                resolved_param[k] = values
                continue

            if _in == 'path':
                # multiple values in a path is impossible
                values = [values]

            if (param_schema is not None and param_schema['type'] == 'array'):
                # resolve variable re-assignment, handle explode
                values = self._resolve_param_duplicates(values, param_defn, _in)
                # handle array styles
                resolved_param[k] = self._split(values, param_defn, _in)
            else:
                resolved_param[k] = values[-1]

        # set defaults if values have not been set yet
        resolved_param = self.set_default_values(resolved_param, self.param_schemas)

        return resolved_param

    def set_default_values(self, _dict, _properties):
        """set recursively default values in objects/dicts"""
        for p_id, property in _properties.items():
            if 'default' in property and p_id not in _dict:
                _dict[p_id] = property['default']
            elif property.get('type', False) == 'object' and 'properties' in property:
                _dict.setdefault(p_id, {})
                _dict[p_id] = self.set_default_values(_dict[p_id], property['properties'])
        return _dict

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            def coerce_dict(md):
                """ MultiDict -> dict of lists
                """
                try:
                    return md.to_dict(flat=False)
                except AttributeError:
                    return dict(md.items())

            query = coerce_dict(request.query)
            path_params = coerce_dict(request.path_params)
            form = coerce_dict(request.form)

            request.query = self.resolve_query(query)
            request.path_params = self.resolve_path(path_params)
            request.form = self.resolve_form(form)
            response = function(request)
            return response

        return wrapper


class OpenAPIURIParser(AbstractURIParser):
    style_defaults = {"path": "simple", "header": "simple",
                      "query": "form", "cookie": "form",
                      "form": "form"}

    @property
    def param_defns(self):
        return self._param_defns

    @property
    def form_defns(self):
        return {k: v for k, v in self._body_schema.get('properties', {}).items()}

    @property
    def param_schemas(self):
        return {k: v.get('schema', {}) for k, v in self.param_defns.items()}

    def resolve_form(self, form_data):
        if self._body_schema is None or self._body_schema.get('type') != 'object':
            return form_data
        for k in form_data:
            encoding = self._body_encoding.get(k, {"style": "form"})
            defn = self.form_defns.get(k, {})
            # TODO support more form encoding styles
            form_data[k] = \
                self._resolve_param_duplicates(form_data[k], encoding, 'form')
            if defn and defn["type"] == "array":
                form_data[k] = self._split(form_data[k], encoding, 'form')
        return form_data

    def resolve_query(self, query_data):
        return self.resolve_params(query_data, 'query')

    def resolve_path(self, path_data):
        return self.resolve_params(path_data, 'path')

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the first-defined value.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "4,5,6".
            However, if 'explode' is 'True' then the duplicate values
            are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        default_style = OpenAPIURIParser.style_defaults[_in]
        style = param_defn.get('style', default_style)
        delimiter = QUERY_STRING_DELIMITERS.get(style, ',')
        is_form = (style == 'form')
        explode = param_defn.get('explode', is_form)
        if explode:
            return delimiter.join(values)

        # default to last defined value
        return values[-1]

    @staticmethod
    def _split(value, param_defn, _in):
        default_style = OpenAPIURIParser.style_defaults[_in]
        style = param_defn.get('style', default_style)
        delimiter = QUERY_STRING_DELIMITERS.get(style, ',')
        return value.split(delimiter)


class Swagger2URIParser(AbstractURIParser):
    """
    Adheres to the Swagger2 spec,
    Assumes the the last defined query parameter should be used.
    """
    parsable_parameters = ["query", "path", "formData"]

    @property
    def param_defns(self):
        return self._param_defns

    @property
    def param_schemas(self):
        return self._param_defns  # swagger2 conflates defn and schema

    def resolve_form(self, form_data):
        return self.resolve_params(form_data, 'form')

    def resolve_query(self, query_data):
        return self.resolve_params(query_data, 'query')

    def resolve_path(self, path_data):
        return self.resolve_params(path_data, 'path')

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the first-defined value.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "4,5,6".
            However, if 'collectionFormat' is 'multi' then the duplicate values
            are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get('collectionFormat') == 'multi':
            return ','.join(values)
        # default to last defined value
        return values[-1]

    @staticmethod
    def _split(value, param_defn, _in):
        if param_defn.get("collectionFormat") == 'pipes':
            return value.split('|')
        return value.split(',')


class FirstValueURIParser(Swagger2URIParser):
    """
    Adheres to the Swagger2 spec
    Assumes that the first defined query parameter should be used
    """

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the first-defined value.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "1,2,3".
            However, if 'collectionFormat' is 'multi' then the duplicate values
            are concatenated together and `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get('collectionFormat') == 'multi':
            return ','.join(values)
        # default to first defined value
        return values[0]


class AlwaysMultiURIParser(Swagger2URIParser):
    """
    Does not adhere to the Swagger2 spec, but is backwards compatible with
    connexion behavior in version 1.4.2
    """

    @staticmethod
    def _resolve_param_duplicates(values, param_defn, _in):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to join all provided parameters together.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "1,2,3,4,5,6".
        """
        if param_defn.get('collectionFormat') == 'pipes':
            return '|'.join(values)
        return ','.join(values)
