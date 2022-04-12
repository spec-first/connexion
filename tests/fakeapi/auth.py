import asyncio
import json

from connexion.exceptions import OAuthProblem


def fake_basic_auth(username, password, required_scopes=None):
    if username == password:
        return {'uid': username}
    return None


def fake_json_auth(token, required_scopes=None):
    try:
        return json.loads(token)
    except ValueError:
        return None


async def async_basic_auth(username, password, required_scopes=None, request=None):
    return fake_basic_auth(username, password, required_scopes)


async def async_json_auth(token, required_scopes=None, request=None):
    return fake_json_auth(token, required_scopes)


async def async_scope_validation(required_scopes, token_scopes, request):
    return required_scopes == token_scopes

async def async_auth_exception(token, required_scopes=None, request=None):
    raise OAuthProblem
