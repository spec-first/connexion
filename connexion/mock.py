
from functools import partial

from connexion.resolver import Resolver, Resolution, ResolverError


class MockResolver(Resolver):

    def __init__(self, mock_all):
        # needs to be set after creating the Api instance
        self.api = None
        self.mock_all = mock_all
        self._operation_id_counter = 1

    def resolve(self, operation):
        """
        Mock operation resolver

        :type operation: connexion.operation.Operation
        """
        operation_id = self.resolve_operation_id(operation)
        if not operation_id:
            # just generate an unique operation ID
            operation_id = 'mock-{}'.format(self._operation_id_counter)
            self._operation_id_counter += 1

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
        # simply use the first/lowest status code, this is probably 200 or 201
        status_code = sorted(response_definitions.keys())[0]
        response_definition = response_definitions.get(status_code, {})
        response_definition = operation.resolve_reference(response_definition)
        examples = response_definition.get('examples')
        if examples:
            return list(examples.values())[0], status_code
        else:
            return 'No example response was defined.', status_code
