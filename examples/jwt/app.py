"""
Basic example of a resource server
"""
import time
from pathlib import Path

import connexion
from jose import JWTError, jwt
from werkzeug.exceptions import Unauthorized

JWT_ISSUER = "com.zalando.connexion"
JWT_SECRET = "change_this"
JWT_LIFETIME_SECONDS = 600
JWT_ALGORITHM = "HS256"


def generate_token(user_id):
    timestamp = _current_timestamp()
    payload = {
        "iss": JWT_ISSUER,
        "iat": int(timestamp),
        "exp": int(timestamp + JWT_LIFETIME_SECONDS),
        "sub": str(user_id),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise Unauthorized from e


def get_secret(user, token_info) -> str:
    return """
    You are user_id {user} and the secret is 'wbevuec'.
    Decoded token claims: {token_info}.
    """.format(
        user=user, token_info=token_info
    )


def _current_timestamp() -> int:
    return int(time.time())


app = connexion.FlaskApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml")


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
