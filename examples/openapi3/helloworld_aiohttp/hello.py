#!/usr/bin/env python3
import asyncio

import connexion
from aiohttp import web


@asyncio.coroutine
def post_greeting(name):
    return web.Response(text='Hello {name}'.format(name=name))


if __name__ == '__main__':
    app = connexion.AioHttpApp(__name__, port=9090, specification_dir='openapi/')
    app.add_api('helloworld-api.yaml', arguments={'title': 'Hello World Example'})
    app.run()
