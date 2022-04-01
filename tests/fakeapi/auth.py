import asyncio
import json


def fake_basic_auth(username, password, required_scopes=None):
    if username == password:
        return {'uid': username}
    return None


def fake_json_auth(token, required_scopes=None):
    try:
        return json.loads(token)
    except ValueError:
        return None
