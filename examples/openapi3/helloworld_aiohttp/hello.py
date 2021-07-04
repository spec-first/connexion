#!/usr/bin/env python3

from aiohttp import web

import connexion


async def post_greeting(name):
    return web.Response(text=f'Hello {name}')


if __name__ == '__main__':
    app = connexion.AioHttpApp(__name__, port=9090, specification_dir='openapi/')
    app.add_api('helloworld-api.yaml', arguments={'title': 'Hello World Example'})
    app.run()
