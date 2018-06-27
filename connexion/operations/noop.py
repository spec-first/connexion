import logging

from connexion.operations.abstract import AbstractOperation

logger = logging.getLogger("connexion.operations.noop")


class NoOperation(AbstractOperation):

    def __init__(self, api, method, path, operation, resolver, app_security=None,
                 security_schemes=None, validate_responses=False,
                 strict_validation=False, randomize_endpoint=None,
                 validator_map=None, pythonic_params=False):

        super(NoOperation, self).__init__(
            api=api,
            method=method,
            path=path,
            operation=operation,
            resolver=resolver,
            app_security=app_security,
            security_schemes=security_schemes,
            validate_responses=validate_responses,
            strict_validation=strict_validation,
            randomize_endpoint=randomize_endpoint,
            pythonic_params=pythonic_params,
            validator_map=validator_map
        )

    def _resolve_reference(self, _):
        pass

    def _spec_definitions(self):
        pass

    def _validate_defaults(self):
        pass

    @property
    def body_definition(self):
        pass

    @property
    def body_schema(self):
        pass

    @property
    def consumes(self):
        pass

    @property
    def produces(self):
        pass

    @property
    def example_response(self):
        pass

    def get_path_parameter_types(self):
        pass
