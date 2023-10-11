"""
This module contains resolvers, functions that resolves the user defined view functions
from the operations defined in the OpenAPI spec.
"""

import inspect
import logging
import typing as t

from inflection import camelize

import connexion.utils as utils
from connexion.exceptions import ResolverError

logger = logging.getLogger("connexion.resolver")


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
    def __init__(self, function_resolver: t.Callable = utils.get_function_from_name):
        """
        Standard resolver

        :param function_resolver: Function that resolves functions using an operationId
        """
        self.function_resolver = function_resolver

    def resolve(self, operation):
        """
        Default operation resolver

        :type operation: connexion.operations.AbstractOperation
        """
        operation_id = self.resolve_operation_id(operation)
        return Resolution(
            self.resolve_function_from_operation_id(operation_id), operation_id
        )

    def resolve_operation_id(self, operation):
        """
        Default operationId resolver

        :type operation: connexion.operations.AbstractOperation
        """
        operation_id = operation.operation_id
        router_controller = operation.router_controller
        if router_controller is None:
            return operation_id
        return f"{router_controller}.{operation_id}"

    def resolve_function_from_operation_id(self, operation_id):
        """
        Invokes the function_resolver

        :type operation_id: str
        """
        try:
            return self.function_resolver(operation_id)
        except ImportError as e:
            msg = f'Cannot resolve operationId "{operation_id}"! Import error was "{str(e)}"'
            raise ResolverError(msg)
        except (AttributeError, ValueError) as e:
            raise ResolverError(str(e))


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
            return f"{self.root_path}.{operation_id}"
        return f"{router_controller}.{operation_id}"


class RestyResolver(Resolver):
    """
    Resolves endpoint functions using REST semantics (unless overridden by specifying operationId)
    """

    def __init__(
        self, default_module_name: str, *, collection_endpoint_name: str = "search"
    ):
        """
        :param default_module_name: Default module name for operations
        :param collection_endpoint_name: Name of function to resolve collection endpoints to
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
        path_components = [c for c in operation.path.split("/") if len(c)]

        def is_var(component):
            """True if the path component is a var. eg, '{id}'"""
            return (component[0] == "{") and (component[-1] == "}")

        resource_name = ".".join([c for c in path_components if not is_var(c)]).replace(
            "-", "_"
        )

        def get_controller_name():
            x_router_controller = operation.router_controller

            name = self.default_module_name

            if x_router_controller:
                name = x_router_controller

            elif resource_name:
                name += "." + resource_name

            return name

        def get_function_name():
            method = operation.method

            is_collection_endpoint = (
                method.lower() == "get"
                and len(resource_name)
                and not is_var(path_components[-1])
            )

            return (
                self.collection_endpoint_name
                if is_collection_endpoint
                else method.lower()
            )

        return f"{get_controller_name()}.{get_function_name()}"


class MethodResolverBase(RestyResolver):
    """
    Resolves endpoint functions based on Flask's MethodView semantics, e.g.

    .. code-block:: yaml

        paths:
            /foo_bar:
                get:
                    # Implied function call: api.FooBarView().get

    .. code-block:: python

        class FooBarView(MethodView):
            def get(self):
                return ...
            def post(self):
                return ...

    """

    _class_arguments_type = t.Dict[
        str, t.Dict[str, t.Union[t.Iterable, t.Dict[str, t.Any]]]
    ]

    def __init__(self, *args, class_arguments: _class_arguments_type = None, **kwargs):
        """
        :param args: Arguments passed to :class:`~RestyResolver`
        :param class_arguments: Arguments to instantiate the View Class in the format below
        :param kwargs: Keywords arguments passed to :class:`~RestyResolver`

        .. code-block:: python

            {
              "ViewName": {
                "args": (positional arguments,)
                "kwargs": {
                  "keyword": "argument"
                }
              }
            }
        """
        self.class_arguments = class_arguments or {}
        super(MethodResolverBase, self).__init__(*args, **kwargs)
        self.initialized_views: list = []

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
        module_name, view_base, meth_name = operation_id.rsplit(".", 2)
        view_name = camelize(view_base) + "View"

        return f"{module_name}.{view_name}.{meth_name}"

    def resolve_function_from_operation_id(self, operation_id):
        """
        Invokes the function_resolver

        :type operation_id: str
        """

        try:
            module_name, view_name, meth_name = operation_id.rsplit(".", 2)
            if operation_id and not view_name.endswith("View"):
                # If operation_id is not a view then assume it is a standard function
                return self.function_resolver(operation_id)

            mod = __import__(module_name, fromlist=[view_name])
            view_cls = getattr(mod, view_name)
            # find the view and return it
            return self.resolve_method_from_class(view_name, meth_name, view_cls)

        except ImportError as e:
            msg = 'Cannot resolve operationId "{}"! Import error was "{}"'.format(
                operation_id, str(e)
            )
            raise ResolverError(msg)
        except (AttributeError, ValueError) as e:
            raise ResolverError(str(e))

    def resolve_method_from_class(self, view_name, meth_name, view_cls):
        """
        Returns the view function for the given view class.
        """
        raise NotImplementedError()


class MethodResolver(MethodResolverBase):
    """
    A generic method resolver that instantiates a class and extracts the method
    from it, based on the operation id.
    """

    def resolve_method_from_class(self, view_name, meth_name, view_cls):
        view = None
        for v in self.initialized_views:
            if v.__class__ == view_cls:
                view = v
                break
        if view is None:
            # get the args and kwargs for this view
            cls_arguments = self.class_arguments.get(view_name, {})
            cls_args = cls_arguments.get("args", ())
            cls_kwargs = cls_arguments.get("kwargs", {})
            # instantiate the class with the args and kwargs
            view = view_cls(*cls_args, **cls_kwargs)
            self.initialized_views.append(view)
        # get the method if the class
        func = getattr(view, meth_name)
        # Return the method function of the class
        return func


class MethodViewResolver(MethodResolverBase):
    """
    A specialized method resolver that works with flask's method views.
    It resolves the method by calling as_view on the class.
    """

    def __init__(self, *args, **kwargs):
        if "collection_endpoint_name" in kwargs:
            del kwargs["collection_endpoint_name"]
            # Dispatch of request is done by Flask
            logger.warning(
                "collection_endpoint_name is ignored by the MethodViewResolver. "
                "Requests to a collection endpoint will be routed to .get()"
            )
        super().__init__(*args, **kwargs)

    def resolve_method_from_class(self, view_name, meth_name, view_cls):
        view = None
        for v in self.initialized_views:
            # views returned by <class>.as_view
            # have the origin class attached as .view_class
            if v.view_class == view_cls:
                view = v
                break
        if view is None:
            # get the args and kwargs for this view
            cls_arguments = self.class_arguments.get(view_name, {})
            cls_args = cls_arguments.get("args", ())
            cls_kwargs = cls_arguments.get("kwargs", {})
            # call as_view to get a view function
            # that is decorated with the classes
            # decorator list, if any
            view = view_cls.as_view(view_name, *cls_args, **cls_kwargs)
            # add the view to the list of initialized views
            # in order to call as_view only once
            self.initialized_views.append(view)
        # return the class as view function
        # for each operation so that requests
        # are dispatched with <class>.dispatch_request,
        # when calling the view function
        return view
