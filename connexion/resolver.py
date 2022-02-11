"""
This module contains resolvers, functions that resolves the user defined view functions
from the operations defined in the OpenAPI spec.
"""

import inspect
import logging
import sys

import connexion.utils as utils
from connexion.exceptions import ResolverError

logger = logging.getLogger('connexion.resolver')


class Resolution:
    def __init__(self, function, operation_id):
        """
        Represents the result of operation resolution

        :param function: The endpoint function
        :type function: types.FunctionType
        """
        self.function = function
        self.operation_id = operation_id


class Resolver:
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

        :type operation: connexion.operations.AbstractOperation
        """
        operation_id = self.resolve_operation_id(operation)
        return Resolution(self.resolve_function_from_operation_id(operation_id), operation_id)

    def resolve_operation_id(self, operation):
        """
        Default operationId resolver

        :type operation: connexion.operations.AbstractOperation
        """
        operation_id = operation.operation_id
        router_controller = operation.router_controller
        if router_controller is None:
            return operation_id
        return f'{router_controller}.{operation_id}'

    def resolve_function_from_operation_id(self, operation_id):
        """
        Invokes the function_resolver

        :type operation_id: str
        """
        try:
            return self.function_resolver(operation_id)
        except ImportError as e:
            msg = f'Cannot resolve operationId "{operation_id}"! Import error was "{str(e)}"'
            raise ResolverError(msg, sys.exc_info())
        except (AttributeError, ValueError) as e:
            raise ResolverError(str(e), sys.exc_info())


class RelativeResolver(Resolver):
    """
    Resolves endpoint functions relative to a given root path or module.
    """
    def __init__(self, root_path, function_resolver=utils.get_function_from_name):
        """
        :param root_path: The root path relative to which an operationId is resolved.
            Can also be a module. Has the same effect as setting
            `x-swagger-router-controller` or `x-openapi-router-controller` equal to
            `root_path` for every operation individually.
        :type root_path: typing.Union[str, types.ModuleType]
        :param function_resolver: Function that resolves functions using an operationId
        :type function_resolver: types.FunctionType
        """
        super().__init__(function_resolver=function_resolver)
        if inspect.ismodule(root_path):
            self.root_path = root_path.__name__
        else:
            self.root_path = root_path

    def resolve_operation_id(self, operation):
        """Resolves the operationId relative to the root path, unless
        x-swagger-router-controller or x-openapi-router-controller is specified.

        :param operation: The operation to resolve
        :type operation: connexion.operations.AbstractOperation
        """
        operation_id = operation.operation_id
        router_controller = operation.router_controller
        if router_controller is None:
            return f'{self.root_path}.{operation_id}'
        return f'{router_controller}.{operation_id}'


class RestyResolver(Resolver):
    """
    Resolves endpoint functions using REST semantics (unless overridden by specifying operationId)
    """

    def __init__(self, default_module_name, collection_endpoint_name='search'):
        """
        :param default_module_name: Default module name for operations
        :type default_module_name: str
        """
        super().__init__()
        self.default_module_name = default_module_name
        self.collection_endpoint_name = collection_endpoint_name

    def resolve_operation_id(self, operation):
        """
        Resolves the operationId using REST semantics unless explicitly configured in the spec

        :type operation: connexion.operations.AbstractOperation
        """
        if operation.operation_id:
            return super().resolve_operation_id(operation)

        return self.resolve_operation_id_using_rest_semantics(operation)

    def resolve_operation_id_using_rest_semantics(self, operation):
        """
        Resolves the operationId using REST semantics

        :type operation: connexion.operations.AbstractOperation
        """

        # Split the path into components delimited by '/'
        path_components = [c for c in operation.path.split('/') if len(c)]

        def is_var(component):
            """True if the path component is a var. eg, '{id}'"""
            return (component[0] == '{') and (component[-1] == '}')

        resource_name = '.'.join(
            [c for c in path_components if not is_var(c)]
        ).replace('-', '_')

        def get_controller_name():
            x_router_controller = operation.router_controller

            name = self.default_module_name

            if x_router_controller:
                name = x_router_controller

            elif resource_name:
                name += '.' + resource_name

            return name

        def get_function_name():
            method = operation.method

            is_collection_endpoint = \
                method.lower() == 'get' \
                and len(resource_name) \
                and not is_var(path_components[-1])

            return self.collection_endpoint_name if is_collection_endpoint else method.lower()

        return f'{get_controller_name()}.{get_function_name()}'


class MethodViewResolver(RestyResolver):
    """
    Resolves endpoint functions based on Flask's MethodView semantics, e.g. ::

            paths:
                /foo_bar:
                    get:
                        # Implied function call: api.FooBarView().get

            class FooBarView(MethodView):
                def get(self):
                    return ...
                def post(self):
                    return ...
    """

    def __init__(self, *args, **kwargs):
        super(MethodViewResolver, self).__init__(*args, **kwargs)
        self.initialized_views = []

    def resolve_operation_id(self, operation):
        """
        Resolves the operationId using REST semantics unless explicitly configured in the spec
        Once resolved with REST semantics the view_name is capitalised and has 'View' added
        to it so it now matches the Class names of the MethodView

        :type operation: connexion.operations.AbstractOperation
        """
        if operation.operation_id:
            # If operation_id is defined then use the higher level API to resolve
            return RestyResolver.resolve_operation_id(self, operation)

        # Use RestyResolver to get operation_id for us (follow their naming conventions/structure)
        operation_id = self.resolve_operation_id_using_rest_semantics(operation)
        module_name, view_base, meth_name = operation_id.rsplit('.', 2)
        view_name = view_base[0].upper() + view_base[1:] + 'View'

        return f"{module_name}.{view_name}.{meth_name}"

    def resolve_function_from_operation_id(self, operation_id):
        """
        Invokes the function_resolver

        :type operation_id: str
        """

        try:
            module_name, view_name, meth_name = operation_id.rsplit('.', 2)
            if operation_id and not view_name.endswith('View'):
                # If operation_id is not a view then assume it is a standard function
                return self.function_resolver(operation_id)

            mod = __import__(module_name, fromlist=[view_name])
            view_cls = getattr(mod, view_name)
            # Find the class and instantiate it
            view = None
            for v in self.initialized_views:
                if v.__class__ == view_cls:
                    view = v
                    break
            if view is None:
                view = view_cls()
                self.initialized_views.append(view)
            func = getattr(view, meth_name)
            # Return the method function of the class
            return func
        except ImportError as e:
            msg = 'Cannot resolve operationId "{}"! Import error was "{}"'.format(
                operation_id, str(e))
            raise ResolverError(msg, sys.exc_info())
        except (AttributeError, ValueError) as e:
            raise ResolverError(str(e), sys.exc_info())
