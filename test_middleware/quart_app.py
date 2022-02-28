from quart import Quart, json, request


from connexion.middleware import ConnexionMiddleware, TestMiddleware


# Simple Flask app. Can be any WSGI framework if we use WsgiToAsgi adapter.

app = Quart(__name__)


@app.route('/test')
def test():
    value = request.args.get('int')

    if value == '1':
        value = int(value)

    return json.dumps({'int': value})


# Add connexion middleware.

middlewares = ConnexionMiddleware.default_middlewares + [TestMiddleware]

app = ConnexionMiddleware(app, middlewares=middlewares)
app.add_api('openapi.yaml')
