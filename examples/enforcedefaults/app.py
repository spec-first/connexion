from pathlib import Path

import connexion
from connexion.validators import DefaultsJSONRequestBodyValidator


def echo(data):
    return data


validator_map = {"body": {"application/json": DefaultsJSONRequestBodyValidator}}


app = connexion.AsyncApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml", validator_map=validator_map)
app.add_api("swagger.yaml", validator_map=validator_map)


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
