"""
example of connexion running behind a path-altering reverse-proxy

NOTE this demo is not secure by default!!
You'll want to make sure these headers are coming from your proxy, and not
directly from users on the web!

"""
import logging
from pathlib import Path

import connexion
import uvicorn
from starlette.types import Receive, Scope, Send


class ReverseProxied:
    """Wrap the application in this middleware and configure the
    reverse proxy to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:

    location /proxied {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Path /proxied;
    }

    :param app: the WSGI application
    :param root_path: override the default script name (path)
    :param scheme: override the default scheme
    :param server: override the default server
    """

    def __init__(self, app, root_path=None, scheme=None, server=None):
        self.app = app
        self.root_path = root_path
        self.scheme = scheme
        self.server = server

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        logging.warning(
            "this demo is not secure by default!! "
            "You'll want to make sure these headers are coming from your proxy, "
            "and not directly from users on the web!"
        )
        root_path = scope.get("root_path") or self.root_path
        for header, value in scope.get("headers", []):
            if header == b"x-forwarded-path":
                root_path = value.decode()
                break
        if root_path:
            root_path = "/" + root_path.strip("/")
            scope["root_path"] = root_path
            scope["path"] = root_path + scope.get("path", "")
            scope["raw_path"] = root_path.encode() + scope.get("raw_path", "")

        scope["scheme"] = scope.get("scheme") or self.scheme
        scope["server"] = scope.get("server") or (self.server, None)

        return await self.app(scope, receive, send)


def hello():
    return "hello"


def create_app():
    app = connexion.FlaskApp(__name__, specification_dir="spec")
    app.add_api("openapi.yaml")
    app.add_api("swagger.yaml")
    app.middleware = ReverseProxied(app.middleware, root_path="/reverse_proxied/")
    return app


if __name__ == "__main__":
    uvicorn.run(
        f"{Path(__file__).stem}:create_app", factory=True, port=8080, proxy_headers=True
    )
