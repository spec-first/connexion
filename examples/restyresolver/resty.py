import logging
from pathlib import Path

import connexion
from connexion.resolver import RestyResolver

logging.basicConfig(level=logging.INFO)

app = connexion.FlaskApp(__name__, specification_dir="spec")
app.add_api(
    "openapi.yaml",
    arguments={"title": "RestyResolver Example"},
    resolver=RestyResolver("api"),
)
app.add_api(
    "swagger.yaml",
    arguments={"title": "RestyResolver Example"},
    resolver=RestyResolver("api"),
)


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
