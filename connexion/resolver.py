"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import logging
import re
import connexion.utils as utils

logger = logging.getLogger('connexion.resolver')


class Resolution:
    def __init__(self, function, operation_id):
        """
        Represents the result of operation resolution

        :param function: The endpoint function
        :type function: function
        """
        self.function = function
        self.operation_id = operation_id


class Resolver:
    """
    Standard resolver
    """

    def resolve(self, operation):
        """
        Default operation resolver

        :type operation: Operation
        """
        operation_id = self.resolve_operation_id(operation)
        return Resolution(self.resolve_function_from_operation_id(operation_id), operation_id)

    def resolve_operation_id(self, operation):
        """
        Default operationId resolver

        :type operation: Operation
        """
        spec = operation.operation
        operation_id = spec.get('operationId')
        x_router_controller = spec.get('x-swagger-router-controller')
        if x_router_controller is None:
            return operation_id
        return x_router_controller + '.' + operation_id

    def resolve_function_from_operation_id(self, operation_id):
        """
        Default function resolver, tries to get function by fully qualified name (e.g. "mymodule.myobj.myfunc")

        :type operation_id: str
        """
        return utils.get_function_from_name(operation_id)


class RestyResolver(Resolver):
    """
    Resolves endpoint functions using REST semantics (unless overridden by specifying operationId)
    """

    def __init__(self, default_module_name, collection_endpoint_name='search'):
        """
        :param default_module_name: Default module name for operations
        :type default_module_name: string
        """
        self.default_module_name = default_module_name
        self.collection_endpoint_name = collection_endpoint_name

    def resolve_operation_id(self, operation):

        spec = operation.operation
        operation_id = spec.get('operationId')

        if operation_id:
            return Resolver.resolve_operation_id(self, operation)

        function = operation.method.lower()
        x_router_controller = spec.get('x-swagger-router-controller')

        if x_router_controller:
            mod_name = x_router_controller
        else:
            mod_name = self.default_module_name
            match = re.search('^/(.+?)(/.?|$)', operation.path)
            if match:
                mod_name += '.' + match.group(1)
                if function == 'get' and match.group(2).strip('/') == '':
                    function = self.collection_endpoint_name

        operation_id = mod_name + '.' + function

        return operation_id
