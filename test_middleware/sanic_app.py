from sanic import Sanic
from sanic.response import json


from connexion.middleware import ConnexionMiddleware, SwaggerUIMiddleware, TestMiddleware


# Simple Sanic app. Can be any ASGI framework.

app = Sanic('test')


@app.route('/test')
async def test(request):
    value = request.args.get('int')

    if value == '1':
        value = int(value)

    return json({'int': value})


# Add connexion middleware.

middlewares = ConnexionMiddleware.default_middlewares + [TestMiddleware]

app = ConnexionMiddleware(app, middlewares=middlewares)
app.add_api('openapi.yaml')
