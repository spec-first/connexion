from pathlib import Path

import connexion
import jsonschema
from connexion.json_schema import Draft4RequestValidator
from connexion.validators import JSONRequestBodyValidator


# TODO: should work as sync endpoint when parameter decorator is fixed
async def echo(data):
    return data


# via https://python-jsonschema.readthedocs.io/
def extend_with_set_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        yield from validate_properties(validator, properties, instance, schema)

    return jsonschema.validators.extend(validator_class, {"properties": set_defaults})


DefaultsEnforcingDraft4Validator = extend_with_set_default(Draft4RequestValidator)


class DefaultsEnforcingRequestBodyValidator(JSONRequestBodyValidator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validator=DefaultsEnforcingDraft4Validator, **kwargs)


validator_map = {"body": {"application/json": DefaultsEnforcingRequestBodyValidator}}


app = connexion.AsyncApp(__name__, specification_dir="spec")
app.add_api("swagger.yaml", validator_map=validator_map)


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
