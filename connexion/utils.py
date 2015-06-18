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


def flaskify_endpoint(identifier: str) -> str:
    """
    Converts the provided identifier in a valid flask endpoint name
    """
    return identifier.replace('.', '_')


def flaskify_path(swagger_path: str) -> str:
    """
    Convert swagger path templates to flask path templates
    """
    translation_table = str.maketrans('{-}', '<_>')
    # TODO add types
    return swagger_path.translate(translation_table)


def get_function_from_name(operation_id: str) -> str:
    module_name, function_name = operation_id.rsplit('.', maxsplit=1)
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    return function


def produces_json(produces: list) -> bool:
    """
    >>> produces_json(['application/json'])
    True
    >>> produces_json(['application/x.custom+json'])
    True
    >>> produces_json([])
    False
    >>> produces_json(['application/xml'])
    False
    >>> produces_json(['text/json'])
    False
    >>> produces_json(['application/json', 'other/type'])
    False
    """
    if len(produces) != 1:
        return False

    mimetype = produces[0]  # type: str
    if mimetype == 'application/json':
        return True

    # todo handle parameters
    maintype, subtype = mimetype.split('/')  # type: str, str
    return maintype == 'application' and subtype.endswith('+json')
