import functools
import importlib
import re

import six
import yaml

# Python 2/3 compatibility:
try:
    py_string = unicode
except NameError:  # pragma: no cover
    py_string = str  # pragma: no cover


def boolean(s):
    '''
    Convert JSON/Swagger boolean value to Python, raise ValueError otherwise

    >>> boolean('true')
    True

    >>> boolean('false')
    False
    '''
    if isinstance(s, bool):
        return s
    elif not hasattr(s, 'lower'):
        raise ValueError('Invalid boolean value')
    elif s.lower() == 'true':
        return True
    elif s.lower() == 'false':
        return False
    else:
        raise ValueError('Invalid boolean value')


# https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
TYPE_MAP = {'integer': int,
            'number': float,
            'string': py_string,
            'boolean': boolean,
            'array': list,
            'object': dict}  # map of swagger types to python types


def make_type(value, _type):
    type_func = TYPE_MAP[_type]  # convert value to right type
    return type_func(value)


def deep_getattr(obj, attr):
    """
    Recurses through an attribute chain to get the ultimate value.

    Stolen from http://pingfive.typepad.com/blog/2010/04/deep-getattr-python-function.html
    """
    return functools.reduce(getattr, attr.split('.'), obj)


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
    try:
        return deep_get(obj[int(keys[0])], keys[1:])
    except ValueError:
        return deep_get(obj[keys[0]], keys[1:])


def get_function_from_name(function_name):
    """
    Tries to get function by fully qualified name (e.g. "mymodule.myobj.myfunc")

    :type function_name: str
    """
    if function_name is None:
        raise ValueError("Empty function name")

    if '.' in function_name:
        module_name, attr_path = function_name.rsplit('.', 1)
    else:
        module_name = ''
        attr_path = function_name

    module = None
    last_import_error = None

    while not module:
        try:
            module = importlib.import_module(module_name)
        except ImportError as import_error:
            last_import_error = import_error
            if '.' in module_name:
                module_name, attr_path1 = module_name.rsplit('.', 1)
                attr_path = '{0}.{1}'.format(attr_path1, attr_path)
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
    maintype, subtype = mimetype.split('/')  # type: str, str
    return maintype == 'application' and (subtype == 'json' or subtype.endswith('+json'))


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
    return (
        param_def.get('schema', param_def).get('nullable', False) or
        param_def.get('x-nullable', False)  # swagger2
    )


def is_null(value):
    if hasattr(value, 'strip') and value.strip() in ['null', 'None']:
        return True

    if value is None:
        return True

    return False


class Jsonifier(object):
    def __init__(self, json_):
        self.json = json_

    def dumps(self, data):
        """ Central point where JSON serialization happens inside
        Connexion.
        """
        return "{}\n".format(self.json.dumps(data, indent=2))

    def loads(self, data):
        """ Central point where JSON serialization happens inside
        Connexion.
        """
        if isinstance(data, six.binary_type):
            data = data.decode()

        try:
            return self.json.loads(data)
        except Exception:
            if isinstance(data, six.string_types):
                return data


def has_coroutine(function, api=None):
    """
    Checks if function is a coroutine.
    If ``function`` is a decorator (has a ``__wrapped__`` attribute)
    this function will also look at the wrapped function.
    """
    if six.PY3:  # pragma: 2.7 no cover
        import asyncio

        def iscorofunc(func):
            iscorofunc = asyncio.iscoroutinefunction(func)
            while not iscorofunc and hasattr(func, '__wrapped__'):
                func = func.__wrapped__
                iscorofunc = asyncio.iscoroutinefunction(func)
            return iscorofunc

        if api is None:
            return iscorofunc(function)

        else:
            return any(
                iscorofunc(func) for func in (
                    function, api.get_request, api.get_response
                )
            )
    else:  # pragma: 3 no cover
        # there's no asyncio in python 2
        return False


def yamldumper(openapi):
    """
    Returns a nicely-formatted yaml spec.
    :param openapi: a spec dictionary.
    :return: a nicely-formatted, serialized yaml spec.
    """
    def should_use_block(value):
        char_list = (
          u"\u000a"  # line feed
          u"\u000d"  # carriage return
          u"\u001c"  # file separator
          u"\u001d"  # group separator
          u"\u001e"  # record separator
          u"\u0085"  # next line
          u"\u2028"  # line separator
          u"\u2029"  # paragraph separator
        )
        for c in char_list:
            if c in value:
                return True
        return False

    def my_represent_scalar(self, tag, value, style=None):
        if should_use_block(value):
            style = '|'
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


def create_empty_dict_from_list(_list, _dict, _end_value):
    """create from ['foo', 'bar'] a dict like {'foo': {'bar': {}}} recursively. needed for converting query params"""
    current_key = _list.pop(0)
    if _list:
        return {current_key: create_empty_dict_from_list(_list, _dict, _end_value)}
    else:
        return {current_key: _end_value}
