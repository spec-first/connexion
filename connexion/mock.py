
from functools import partial
from connexion.resolver import Resolver, Resolution, ResolverError


class MockResolver(Resolver):

    def __init__(self, mock_all):
        # needs to be set after creating the Api instance
        self.api = None
        self.mock_all = mock_all

    def resolve(self, operation):
        """
        Default operation resolver

        :type operation: connexion.operation.Operation
        """
        operation_id = self.resolve_operation_id(operation)
        mock_func = partial(self.mock_operation, operation=operation)
        if self.mock_all:
            func = mock_func
        else:
            try:
                func = self.resolve_function_from_operation_id(operation_id)
            except ResolverError:
                func = mock_func
        return Resolution(func, operation_id)

    def mock_operation(self, operation, *args, **kwargs):
        response_definitions = operation.operation["responses"]
        response_definition = response_definitions.get(str(200), {})
        response_definition = operation.resolve_reference(response_definition)
        examples = response_definition.get('examples')
        if examples:
            return list(examples.values())[0]
        else:
            return 'TODO'
