import logging
import sys

import connexion.utils as utils
from connexion.exceptions import ResolverError

logger = logging.getLogger('connexion.resolver')


class Resolution(object):
    def __init__(self, function, operation_id):
        """
        Represents the result of operation resolution

        :param function: The endpoint function
        :type function: types.FunctionType
        """
        self.function = function
        self.operation_id = operation_id


class Resolver(object):
    def __init__(self, function_resolver=utils.get_function_from_name):
        """
        Standard resolver

        :param function_resolver: Function that resolves functions using an operationId
        :type function_resolver: types.FunctionType
        """
        self.function_resolver = function_resolver

    def resolve(self, operation):
        """
        Default operation resolver

        :type operation: connexion.operation.Operation
        """
        operation_id = self.resolve_operation_id(operation)
        return Resolution(self.resolve_function_from_operation_id(operation_id), operation_id)

    def resolve_operation_id(self, operation):
        """
        Default operationId resolver

        :type operation: connexion.operation.Operation
        """
        spec = operation.operation
        operation_id = spec.get('operationId', '')
        x_router_controller = spec.get('x-swagger-router-controller')
        if x_router_controller is None:
            return operation_id
        return '{}.{}'.format(x_router_controller, operation_id)

    def resolve_function_from_operation_id(self, operation_id):
        """
        Invokes the function_resolver

        :type operation_id: str
        """
        try:
            return self.function_resolver(operation_id)
        except ImportError as e:
            msg = 'Cannot resolve operationId "{}"! Import error was "{}"'.format(operation_id, str(e))
            raise ResolverError(msg, sys.exc_info())
        except (AttributeError, ValueError) as e:
            raise ResolverError(str(e), sys.exc_info())


class RestyResolver(Resolver):
    """
    Resolves endpoint functions using REST semantics (unless overridden by specifying operationId)
    """

    def __init__(self, default_module_name, collection_endpoint_name='search', module_separator='.'):
        """
        :param default_module_name: Default module name for operations
        :type default_module_name: str
        """
        Resolver.__init__(self)
        self.default_module_name = default_module_name
        self.collection_endpoint_name = collection_endpoint_name
        self.module_separator = module_separator

    def resolve_operation_id(self, operation):
        """
        Resolves the operationId using REST semantics unless explicitly configured in the spec

        :type operation: connexion.operation.Operation
        """
        if operation.operation.get('operationId'):
            return Resolver.resolve_operation_id(self, operation)

        return self.resolve_operation_id_using_rest_semantics(operation)

    def resolve_operation_id_using_rest_semantics(self, operation):
        """
        Resolves the operationId using REST semantics

        :type operation: connexion.operation.Operation
        """
        path_fragments = operation.path.split('/')

        tail_parameter = ''
        has_trailing_slash = False
        if path_fragments:
            tail = path_fragments[-1]
            if tail == '':
                has_trailing_slash = True
            elif tail.startswith('{'):
                tail_parameter = path_fragments.pop()
        logger.debug('Has trailing slash: %s', has_trailing_slash)
        logger.debug('Tail parameter: %s', tail_parameter)

        resource_names = [resource_name for resource_name in path_fragments if resource_name]
        logger.debug('Resource names: %s', resource_names)

        def get_controller_name():
            x_router_controller = operation.operation.get('x-swagger-router-controller')

            name = self.default_module_name

            if x_router_controller:
                name = x_router_controller
                logger.debug('Controller name from router controller: %s', x_router_controller)

            elif resource_names:
                converted_resource_names = [
                    resource_name.replace('-', '_').strip('{}') for resource_name in resource_names
                ]
                name = self.module_separator.join([name] + converted_resource_names)
                logger.debug('Controller name from resource names: %s', name)

            else:
                logger.debug('Controller name from default module name: %s', name)

            return name

        def get_function_name():
            method = operation.method.lower()

            is_collection_endpoint = \
                method == 'get' \
                and resource_names \
                and not (has_trailing_slash or tail_parameter)
            logger.debug('Use "search" function: %s', is_collection_endpoint)

            return self.collection_endpoint_name if is_collection_endpoint else method

        return '{}.{}'.format(get_controller_name(), get_function_name())
