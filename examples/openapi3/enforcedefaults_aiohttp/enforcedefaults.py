#!/usr/bin/env python3

import jsonschema
import six

import especifico
from especifico.decorators.validation import RequestBodyValidator
from especifico.json_schema import Draft4RequestValidator


async def echo(body):
    return body


# via https://python-jsonschema.readthedocs.io/
def extend_with_set_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in six.iteritems(properties):
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return jsonschema.validators.extend(validator_class, {"properties": set_defaults})


DefaultsEnforcingDraft4Validator = extend_with_set_default(Draft4RequestValidator)


class DefaultsEnforcingRequestBodyValidator(RequestBodyValidator):
    def __init__(self, *args, **kwargs):
        super(DefaultsEnforcingRequestBodyValidator, self).__init__(
            *args, validator=DefaultsEnforcingDraft4Validator, **kwargs,
        )


validator_map = {"body": DefaultsEnforcingRequestBodyValidator}


if __name__ == "__main__":
    app = especifico.AioHttpApp(
        __name__, port=8080, specification_dir=".", options={"swagger_ui": True},
    )
    app.add_api(
        "enforcedefaults-api.yaml",
        arguments={"title": "Hello World Example"},
        validator_map=validator_map,
    )
    app.run()
