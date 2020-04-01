import connexion
from aiohttp import web

async def length(body):
    return web.json_response(len(body))

if __name__ == '__main__':
    app = connexion.AioHttpApp(
        __name__,
        port=8080,
        specification_dir='.',
        options={'client_max_size': 100 * 1024 * 1024},
    )
    app.add_api('schema.yaml')
    app.run()
