# Decorators to split query string
import abc
import functools
import logging
import six

from .decorator import BaseDecorator

logger = logging.getLogger('connexion.decorators.query_parser')

QUERY_STRING_DELIMITERS = {
    'spaceDelimited': ' ',
    'pipeDelimited': '|',
    'simple': ',',
    'form': ','
}


@six.add_metaclass(abc.ABCMeta)
class BaseParser(BaseDecorator):
    def __init__(self, param_defns):
        """
        """
        self.param_defns = param_defns

    @abc.abstractproperty
    def param_schemas(self):
        """
        """

    def __repr__(self):
        """
        :rtype: str
        """
        return "<{classname}>".format(classname=self.__class__.__name__)

    @abc.abstractmethod
    def _resolve_param_duplicates(self, values, param_defn):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the last-defined value.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "4,5,6".
            However, if 'explode' is true, or the 'collectionFormat' is 'multi'
            (swagger2) then the duplicate values are concatenated together and
            `a` would be "1,2,3,4,5,6".
        """

    @abc.abstractmethod
    def param_split(self, value, param_defn):
        """
        """

    def resolve_params(self, params, resolve_duplicates=False): 
        resolved_param = {}
        for k, values in params.items():
            param_defn = self.param_defns.get(k)
            param_schema = self.param_schemas.get(k)
            if not (param_defn or param_schema):
                # rely on validation
                resolved_param[k] = values
                continue

            if not resolve_duplicates:
                values = [values]

            if (param_schema is not None and param_schema['type'] == 'array'):
                # resolve variable re-assignment, handle explode
                values = self._resolve_param_duplicates(values, param_defn)
                # handle array styles
                resolved_param[k] = self.param_split(values, param_defn)
            else:
                resolved_param[k] = values[-1]

        return resolved_param

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):

            try:
                query = request.query.to_dict(flat=False)
            except AttributeError:
                query = dict(request.query.items())

            try:
                path_params = request.path_params.to_dict(flat=False)
            except AttributeError:
                path_params = dict(request.path_params.items())

            logger.error('query is: %s', query)
            logger.error('path params are: %s', path_params)

            request.query = self.resolve_params(query, resolve_duplicates=True)
            request.path_params = self.resolve_params(path_params)
            response = function(request)
            logger.error('resolved query is: %s', query)
            logger.error('resolved path params are: %s', path_params)
            return response

        return wrapper


class OpenAPIURIParser(BaseParser):

    @property
    def param_schemas(self):
        return {k: v.get("schema", {}) for k, v in self.param_defns.items()}

    @staticmethod
    def param_split(value, param_defn):
        try:
            style = param_defn['style']
            delimiter = QUERY_STRING_DELIMITERS.get(style, ',')
            return value.split(delimiter)
        except KeyError:
            return value.split(',')

    @staticmethod
    def _resolve_param_duplicates(values, param_defn):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the last-defined value.
            For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
            `a` would be "4,5,6".
            However, if 'explode' is true, or the 'collectionFormat' is 'multi'
            (swagger2) then the duplicate values are concatenated together and
            `a` would be "1,2,3,4,5,6".
        """
        try:
            style = param_defn['style']
            delimiter = QUERY_STRING_DELIMITERS.get(style, ',')
            is_form = (style == 'form')
            explode = param_defn.get('explode', is_form)
            if explode:
                return delimiter.join(values)
        except KeyError:
            if param_defn.get('collectionFormat') == 'multi':
                return ','.join(values)
        # default to last defined value
        return values[-1]


class Swagger2URIParser(BaseParser):

    @property
    def param_schemas(self):
        return self.param_defns  # swagger2 conflates defn and schema

    @staticmethod
    def _resolve_param_duplicates(values, param_defn):
        """ Resolve cases where query parameters are provided multiple times.
            The default behavior is to use the last-defined value.
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
    def param_split(value, param_defn):
        if param_defn.get("collectionFormat") == 'pipes':
            return value.split('|')
        return value.split(',')
