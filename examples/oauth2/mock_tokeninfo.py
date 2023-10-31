"""
Mock OAuth2 token info
"""

import connexion
import uvicorn
from connexion import request

# our hardcoded mock "Bearer" access tokens
TOKENS = {"123": "jdoe", "456": "rms"}


def get_tokeninfo() -> dict:
    try:
        _, access_token = request.headers["Authorization"].split()
    except Exception:
        access_token = ""

    sub = TOKENS.get(access_token)

    if not sub:
        return "No such token", 401

    return {"sub": sub, "scope": ["uid"]}


if __name__ == "__main__":
    app = connexion.FlaskApp(__name__, specification_dir="spec")
    app.add_api("mock_tokeninfo.yaml")
    uvicorn.run(app, port=7979)
