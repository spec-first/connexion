from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from connexion.middleware import ConnexionMiddleware, TestMiddleware


# Simple Starlette app. Can be any ASGI framework.

async def test(request):
    value = request.query_params.get('int')

    if value == '1':
        value = int(value)

    return JSONResponse({'int': value})


app = Starlette(debug=True, routes=[
    Route('/test', test),
])


# Add connexion middleware.

middlewares = ConnexionMiddleware.default_middlewares + [TestMiddleware]

app = ConnexionMiddleware(app, middlewares=middlewares)
app.add_api('openapi.yaml')
