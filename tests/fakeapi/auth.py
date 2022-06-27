import json

from connexion.exceptions import OAuthProblem


def fake_basic_auth(username, password, required_scopes=None):
    if username == password:
        return {"uid": username}
    return None


def fake_json_auth(token, required_scopes=None):
    try:
        return json.loads(token)
    except ValueError:
        return None


async def async_auth_exception(token, required_scopes=None, request=None):
    raise OAuthProblem
