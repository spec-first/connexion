from .utils import boolean, is_null, is_nullable

TYPE_MAP = {
    'integer': int,
    'number': float,
    'boolean': boolean
}


class TypeValidationError(Exception):
    def __init__(self, schema_type, parameter_type, parameter_name):
        """
        Exception raise when type validation fails

        :type schema_type: str
        :type parameter_type: str
        :type parameter_name: str
        :return:
        """
        self.schema_type = schema_type
        self.parameter_type = parameter_type
        self.parameter_name = parameter_name

    def __str__(self):
        msg = "Wrong type, expected '{schema_type}' for {parameter_type} parameter '{parameter_name}'"
        return msg.format(**vars(self))


def coerce_type(param, value, parameter_type, parameter_name=None):

    def make_type(value, type_literal):
        type_func = TYPE_MAP.get(type_literal)
        return type_func(value)

    param_schema = param.get("schema", param)
    if is_nullable(param_schema) and is_null(value):
        return None

    param_type = param_schema.get('type')
    parameter_name = parameter_name if parameter_name else param.get('name')
    if param_type == "array":
        converted_params = []
        for v in value:
            try:
                converted = make_type(v, param_schema["items"]["type"])
            except (ValueError, TypeError):
                converted = v
            converted_params.append(converted)
        return converted_params
    elif param_type == 'object':
        if param_schema.get('properties'):
            def cast_leaves(d, schema):
                if type(d) is not dict:
                    try:
                        return make_type(d, schema['type'])
                    except (ValueError, TypeError):
                        return d
                for k, v in d.items():
                    if k in schema['properties']:
                        d[k] = cast_leaves(v, schema['properties'][k])
                return d

            return cast_leaves(value, param_schema)
        return value
    else:
        try:
            return make_type(value, param_type)
        except ValueError:
            raise TypeValidationError(param_type, parameter_type, parameter_name)
        except TypeError:
            return value
