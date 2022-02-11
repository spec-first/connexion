#!/usr/bin/env python3

import connexion
import jsonschema
from connexion.decorators.validation import RequestBodyValidator
from connexion.json_schema import Draft4RequestValidator


def echo(data):
    return data


# via https://python-jsonschema.readthedocs.io/
def extend_with_set_default(validator_class):
    validate_properties = validator_class.VALIDATORS['properties']

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if 'default' in subschema:
                instance.setdefault(property, subschema['default'])

        yield from validate_properties(
                validator, properties, instance, schema)

    return jsonschema.validators.extend(
        validator_class, {'properties': set_defaults})

DefaultsEnforcingDraft4Validator = extend_with_set_default(Draft4RequestValidator)


class DefaultsEnforcingRequestBodyValidator(RequestBodyValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, validator=DefaultsEnforcingDraft4Validator, **kwargs)


validator_map = {
    'body': DefaultsEnforcingRequestBodyValidator
}


if __name__ == '__main__':
    app = connexion.FlaskApp(
        __name__, port=8080, specification_dir='.')
    app.add_api('enforcedefaults-api.yaml', validator_map=validator_map)
    app.run()
