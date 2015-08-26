"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import importlib
import re
import strict_rfc3339

PATH_PARAMETER = re.compile(r'\{([^}]*)\}')


def flaskify_endpoint(identifier):
    """
    Converts the provided identifier in a valid flask endpoint name

    :type identifier: str
    :rtype: str
    """
    return identifier.replace('.', '_')


def convert_path_parameter(match):
    return '<{}>'.format(match.group(1).replace('-', '_'))


def flaskify_path(swagger_path):
    """
    Convert swagger path templates to flask path templates

    :type swagger_path: str
    :rtype: str

    >>> flaskify_path('/foo-bar/{my-param}')
    '/foo-bar/<my_param>'
    """
    # TODO add types
    return PATH_PARAMETER.sub(convert_path_parameter, swagger_path)


def get_function_from_name(operation_id):
    """
    :type operation_id: str
    """
    module_name, function_name = operation_id.rsplit('.', 1)
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    return function


def is_json_mimetype(mimetype):
    """
    :type mimetype: str
    :rtype: bool
    """
    maintype, subtype = mimetype.split('/')  # type: str, str
    return maintype == 'application' and (subtype == 'json' or subtype.endswith('+json'))


def produces_json(produces):
    """
    Returns True if all mimetypes in produces are serialized with json

    :type produces: list
    :rtype: bool

    >>> produces_json(['application/json'])
    True
    >>> produces_json(['application/x.custom+json'])
    True
    >>> produces_json([])
    True
    >>> produces_json(['application/xml'])
    False
    >>> produces_json(['text/json'])
    False
    >>> produces_json(['application/json', 'other/type'])
    False
    >>> produces_json(['application/json', 'application/x.custom+json'])
    True
    """
    return all(is_json_mimetype(mimetype) for mimetype in produces)


def validate_date(s):
    '''
    Validate date as defined by "full-date" on http://xml2rfc.ietf.org/public/rfc/html/rfc3339.html#anchor14

    >>> validate_date('foo')
    False

    >>> validate_date('2015-07-31')
    True
    '''
    return strict_rfc3339.validate_rfc3339(s + 'T00:00:00Z')


def boolean(s):
    '''
    Convert JSON/Swagger boolean value to Python, raise ValueError otherwise

    >>> boolean('true')
    True

    >>> boolean('false')
    False
    '''
    if s == 'true':
        return True
    elif s == 'false':
        return False
    else:
        raise ValueError('Invalid boolean value')
