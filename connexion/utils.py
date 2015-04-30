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

        # TODO ADD TYPES
        return swagger_path.replace('{', '<').replace('}', '>')


def get_function_from_name(operation_id: str):
        module_name, function_name = operation_id.rsplit('.', maxsplit=1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        return function
