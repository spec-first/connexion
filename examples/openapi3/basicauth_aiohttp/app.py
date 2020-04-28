#!/usr/bin/env python3
'''
Basic example of a resource server
'''

import uuid

import connexion
from aiohttp.web import middleware


def basic_auth(username, password, *, context, required_scopes=None):
    if username == 'admin' and password == 'secret':
        info = {'sub': 'admin', 'scope': 'secret'}
    elif username == 'foo' and password == 'bar':
        info = {'sub': 'user1', 'scope': ''}
    else:
        # optional: raise exception for custom error response
        return None

    print('authenticated', username, context["uuid"], flush=True)

    return info


async def get_secret(user) -> str:
    return "You are {user} and the secret is 'wbevuec'".format(user=user)


@middleware
async def add_uuid(request, handler):
    request["uuid"] = uuid.uuid4()
    return await handler(request)


if __name__ == '__main__':
    app = connexion.AioHttpApp(
        __name__,
        port=8080,
        specification_dir='.',
        server_args={"middlewares": [add_uuid]},
    )
    app.add_api('openapi.yaml')
    app.run()
