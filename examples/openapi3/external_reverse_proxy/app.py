#!/usr/bin/env python3

import connexion


def hello():
    return "hello"


if __name__ == '__main__':
    app = connexion.FlaskApp(__name__, options={'proxy_uri_prefix_header': 'X-Forwarded-Prefix'})
    app.add_api('openapi/openapi.yaml')
    app.run(port=8080)

