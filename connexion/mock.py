import datetime
import logging

from connexion import NoContent
from connexion.resolver import Resolution, Resolver, ResolverError

logger = logging.getLogger(__name__)

PRIMITIVES = {
  "string": lambda schema: "string",
  "string_email": lambda schema: "user@example.com",
  "string_date": lambda schema: datetime.date.today().isoformat(),
  "string_date-time": lambda schema: datetime.datetime.now().isoformat(),
  "number": lambda schema: numeric_primitive(schema, int),
  "number_float": lambda schema: numeric_primitive(schema, float),
  "integer": lambda schema: numeric_primitive(schema, int),
  "boolean": lambda schema: schema.get('default', True),
}


def numeric_primitive(schema, type_):
    minimum = schema.get('minimum')
    exclusive_minimum = schema.get('exclusiveMinimum', False)
    maximum = schema.get('maximum')
    exclusive_maximum = schema.get('exclusiveMaximum', False)
    default = schema.get('default')

    if default is not None:
        return default

    boundary = 0.01 if type_ is float else 1
    minimum = minimum + boundary if exclusive_minimum else minimum
    maximum = maximum + boundary if exclusive_maximum else maximum

    if minimum is not None and maximum is not None:
        if type_ is int:
            return type_(minimum + maximum) // 2
        else:
            return type_(minimum + maximum) / 2.0
    elif minimum is not None:
        return type_(minimum + 1)
    elif maximum is not None:
        return type_(maximum - 1)
    else:
        return type_()


def primitive(schema):
    kw = dict(type=schema['type'], format=schema.get('format', ''))
    fn = PRIMITIVES.get("{type}_{format}".format(**kw), PRIMITIVES.get("{type}".format(**kw)))

    if fn is not None:
        return fn(schema)

    raise ValueError("Unknown Type: {type}".format(**schema))  # pragma: no cover


def normalize_array(arr):
    if isinstance(arr, (list, tuple, set)):
        return arr
    return [arr]


def sample_from_schema(schema, definitions, include_read_only=True, include_write_only=True):
    ref = schema.get('$ref')
    if ref:
        # Referenced schema
        ref = ref[ref.rfind('/') + 1:] or ''
        ref_schema = definitions.get(ref, {})
        schema = ref_schema

    s_type = schema.get('type')
    s_properties = schema.get('properties')
    s_additional_properties = schema.get('additionalProperties')
    s_items = schema.get('items')

    if 'example' in schema:
        return schema['example']

    if not s_type:
        if s_properties:
            s_type = "object"
        elif s_items:
            s_type = "array"
        else:
            raise ValueError("No type specified?")  # pragma: no cover

    if s_type == "object":
        obj = {}
        if s_properties:
            for name, prop in s_properties.items():
                if prop.get('readOnly', False) and not include_read_only:
                    continue
                if prop.get('writeOnly', False) and not include_write_only:
                    continue
                obj[name] = sample_from_schema(prop, definitions,
                                               include_read_only=include_read_only,
                                               include_write_only=include_write_only)

        if s_additional_properties is True:
            obj['additionalProp1'] = {}
        elif s_additional_properties:
            additional_prop_val = sample_from_schema(s_additional_properties, definitions,
                                                     include_read_only=include_read_only,
                                                     include_write_only=include_write_only)

            for i in range(1, 4):
                obj["additionalProp{}".format(i)] = additional_prop_val
        return obj

    if s_type == "array":
        return [sample_from_schema(s_items, definitions,
                                   include_read_only=include_read_only, include_write_only=include_write_only)]

    if "enum" in schema:
        if "default" in schema:
            return schema["default"]
        return normalize_array(schema["enum"])[0]

    if s_type == "file":
        return

    return primitive(schema)


def partial(func, **frozen):
    """
    Replacement for functools.partial as functools.partial does not work with inspect.py on Python 2.7
    """
    def wrapper(*args, **kwargs):
        for k, v in frozen.items():
            kwargs[k] = v
        return func(*args, **kwargs)
    return wrapper


class MockResolver(Resolver):

    def __init__(self, mock_all):
        super(MockResolver, self).__init__()
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
                msg = "... Successfully resolved operationId '{}'! Mock is *not* used for this operation.".format(
                    operation_id)
                logger.debug(msg)
            except ResolverError as resolution_error:
                logger.debug('... {}! Mock function is used for this operation.'.format(
                    resolution_error.reason.capitalize()))
                func = mock_func
        return Resolution(func, operation_id)

    def mock_operation(self, operation, *args, **kwargs):
        response_definitions = operation.operation["responses"]
        # simply use the first/lowest status code, this is probably 200 or 201
        status_code = sorted(response_definitions.keys())[0]
        response_definition = response_definitions.get(status_code, {})
        try:
            status_code = int(status_code)
        except ValueError:
            status_code = 200
        response_definition = operation.resolve_reference(response_definition)
        examples = response_definition.get('examples')
        if examples:
            return list(examples.values())[0], status_code
        else:
            # No response example, check for schema example
            response_schema = response_definition.get('schema', {})
            if not response_schema:
                return NoContent, status_code
            definitions = response_schema.get('definitions', {})
            schema_example = sample_from_schema(response_schema, definitions)
            if schema_example:
                return schema_example, status_code
            else:
                return 'Cannot generate example response.', status_code
