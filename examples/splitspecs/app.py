from pathlib import Path

import connexion

pets = {
    1: {"name": "Aldo", "registered": "2022-11-28T00:00:00Z"},
    2: {"name": "Bailey", "registered": "2023-11-28T11:11:11Z"},
    3: {"name": "Hugo", "registered": "2024-11-28T22:22:22Z"},
}


def get(petId):
    id_ = int(petId)
    if pets.get(id_) is None:
        return connexion.NoContent, 404
    return pets[id_]


def show():
    # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
    return list(pets.values())


app = connexion.FlaskApp(__name__, specification_dir="spec/")
app.add_api("openapi.yaml", arguments={"title": "Pet Store Rel Ref Example"})
app.add_api("swagger.yaml", arguments={"title": "Pet Store Rel Ref Example"})


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
