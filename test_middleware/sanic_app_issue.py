from sanic import Sanic
from sanic.response import json


from starlette.exceptions import ExceptionMiddleware


app = Sanic('test')


@app.route('/test')
async def test(request):
    value = request.args.get('int')

    if value == '1':
        value = int(value)

    return json({'int': value})


class SimpleMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


wrapped_app = SimpleMiddleware(app)
