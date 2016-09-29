"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import functools
import importlib
import random
import re
import string

import flask
import werkzeug.wrappers

PATH_PARAMETER = re.compile(r'\{([^}]*)\}')

# map Swagger type to flask path converter
# see http://flask.pocoo.org/docs/0.10/api/#url-route-registrations
PATH_PARAMETER_CONVERTERS = {
    'integer': 'int',
    'number': 'float'
}


def flaskify_endpoint(identifier, randomize=None):
    """
    Converts the provided identifier in a valid flask endpoint name

    :type identifier: str
    :param randomize: If specified, add this many random characters (upper case
        and digits) to the endpoint name, separated by a pipe character.
    :type randomize: int | None
    :rtype: str
    """
    result = identifier.replace('.', '_')
    if randomize is None:
        return result

    chars = string.ascii_uppercase + string.digits
    return "{result}|{random_string}".format(
        result=result,
        random_string=''.join(random.SystemRandom().choice(chars) for _ in range(randomize)))


def convert_path_parameter(match, types):
    name = match.group(1)
    swagger_type = types.get(name)
    converter = PATH_PARAMETER_CONVERTERS.get(swagger_type)
    return '<{0}{1}{2}>'.format(converter or '',
                                ':' if converter else '',
                                name.replace('-', '_'))


def flaskify_path(swagger_path, types=None):
    """
    Convert swagger path templates to flask path templates

    :type swagger_path: str
    :type types: dict
    :rtype: str

    >>> flaskify_path('/foo-bar/{my-param}')
    '/foo-bar/<my_param>'

    >>> flaskify_path('/foo/{someint}', {'someint': 'int'})
    '/foo/<int:someint>'
    """
    if types is None:
        types = {}
    convert_match = functools.partial(convert_path_parameter, types=types)
    return PATH_PARAMETER.sub(convert_match, swagger_path)


def is_flask_response(obj):
    """
    Verifies if obj is a default Flask response instance.

    :type obj: object
    :rtype bool

    >>> is_flask_response(redirect('http://example.com/'))
    True
    >>> is_flask_response(flask.Response())
    True
    """
    return isinstance(obj, flask.Response) or isinstance(obj, werkzeug.wrappers.Response)


def deep_getattr(obj, attr):
    """
    Recurses through an attribute chain to get the ultimate value.

    Stolen from http://pingfive.typepad.com/blog/2010/04/deep-getattr-python-function.html
    """
    return functools.reduce(getattr, attr.split('.'), obj)


def get_function_from_name(function_name):
    """
    Tries to get function by fully qualified name (e.g. "mymodule.myobj.myfunc")

    :type function_name: str
    """
    module_name, attr_path = function_name.rsplit('.', 1)
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


def is_nullable(param_def):
    return param_def.get('x-nullable', False)


def is_null(value):
    if hasattr(value, 'strip') and value.strip() in ['null', 'None']:
        return True

    if value is None:
        return True

    return False
