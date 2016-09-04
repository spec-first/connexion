"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import os.path
from collections import deque, namedtuple
from copy import deepcopy
from pathlib import Path

import yaml
from connexion.exceptions import InvalidSpecification
from jinja2 import Template


def load(path, template_args):
    """
    Load a swagger spec.

    :param path: path to spec
    :type path: pathlib.Path
    :param template_args: jinja template args
    :type template_args: dict

    :rtype dict
    """
    resolver = Resolver(template_args)
    pointers = inventory(path, resolver)

    root_data = deepcopy(resolver.get(path, []))

    for pointer in pointers:
        value = {'$ref': '#/' + pointer.key_str} if str(path) == pointer.path \
            else resolver.get(pointer.path, pointer.keys)

        data = root_data
        for key in pointer.root_keys_to[:-1]:
            data = data[key]

        if isinstance(value, dict):
            data = data[pointer.root_keys_to[-1]]
            data.pop('$ref')
            data.update(value)
        else:
            data[pointer.root_keys_to[-1]] = value

    return root_data


class Pointer(object):
    def __init__(self, containing_object, parent, root_keys_to):
        """
        A JSON pointer.

        :param containing_object: json object pointer is a member of
        :type containing_object: dict
        :param parent: file name of the document pointer is within
        :type parent: str
        :param root_keys_to: keys leading to this pointer from the root
        :type root_keys_to: list
        """
        self._containing_object = containing_object
        self._parse_reference(parent)
        self.root_keys_to = root_keys_to

    def __eq__(self, other_pointer):
        return self._containing_object is other_pointer._containing_object and \
            self.root_keys_to == other_pointer.root_keys_to

    def _parse_reference(self, parent):
        optional_document, _, self.key_str = self._containing_object['$ref'].partition('#/')

        self.keys = [key.replace('~1', '/').replace('~0', '~')
                     for key in self.key_str.split('/')] \
            if self.key_str else []

        if optional_document:
            self.path = optional_document if os.path.isabs(optional_document) \
                else str(Path(parent).parent / optional_document)
        else:
            self.path = parent


class Resolver(object):
    def __init__(self, template_args):
        """
        Resolves and caches JSON pointers.

        :param template_args: Jinja template arguments
        :type template_args: dict
        """
        self.cache = {}
        self._template_args = template_args

    def get(self, path, keys):
        """
        Get the value of a JSON pointer.

        :param path: pointer's file path value
        :type path: str
        :param keys: pointer's parsed keys
        :type keys: list
        """
        data = self.cache[path] \
            if path in self.cache else self._load_file(path)

        for key in keys:
            if isinstance(data, list):
                data = data[int(key)]
            else:
                data = data[key]

        return data

    def _load_file(self, path):
        with Path(path).open('rb') as fp:
            contents = fp.read()

            try:
                template = contents.decode()
            except UnicodeDecodeError:
                template = contents.decode('utf-8', 'replace')

            rendered = Template(template).render(self._template_args)
            data = yaml.safe_load(rendered)

        self.cache[path] = data
        return data


def inventory(path, resolver):
    """
    Get a list of all of the JSON pointers within a spec.

    :param path: file name of spec to inventory
    :type path: str
    :param resolver: reference resolver
    :type resolver: swagger.Resolver
    :rtype list of swagger.Pointer
    """
    Fragment = namedtuple('Fragment', ['parent', 'data', 'parent_keys_to', 'root_keys_to'])

    pointers = []
    queue = deque()
    queue.append(Fragment(parent=path, data=resolver.get(path, []),
                          parent_keys_to=[], root_keys_to=[]))

    inventoried_data = set()

    while queue:
        fragment = queue.popleft()

        if isinstance(fragment.data, dict):
            for key in fragment.data:
                if key == '$ref':
                    if id(fragment.data) in inventoried_data:
                        continue

                    pointer = Pointer(fragment.data, fragment.parent, fragment.root_keys_to)

                    try:
                        value = resolver.get(pointer.path, pointer.keys)
                    except IOError:
                        message = "Failed to open file \"{path}\" at {from_root}." \
                            .format(path=pointer.path, from_root=pointer.root_keys_to)
                        raise InvalidSpecification(message)
                    except KeyError:
                        message = "Failed to resolve pointer \"{pointer}\" at {from_root}." \
                            .format(pointer=pointer.key_str, from_root=pointer.root_keys_to)
                        raise InvalidSpecification(message)

                    if isinstance(value, dict):
                        queue.append(Fragment(parent=pointer.path, data=value, parent_keys_to=[],
                                              root_keys_to=fragment.root_keys_to))
                    pointers.append(pointer)
                    inventoried_data.add(id(fragment.data))

                elif isinstance(fragment.data[key], dict):
                    queue.append(Fragment(parent=fragment.parent, data=fragment.data[key],
                                          parent_keys_to=fragment.parent_keys_to + [key],
                                          root_keys_to=fragment.root_keys_to + [key]))

                elif isinstance(fragment.data[key], list):
                    queue.extend([Fragment(parent=fragment.parent, data=data,
                                           parent_keys_to=fragment.parent_keys_to + [key, i],
                                           root_keys_to=fragment.root_keys_to + [key, i])
                                  for i, data in enumerate(fragment.data[key])])

    return pointers
