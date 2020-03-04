#!/usr/bin/env python3

import connexion
import jsonschema
import six
from connexion.decorators.validation import RequestBodyValidator
from connexion.json_schema import Draft4RequestValidator


async def echo(body):
    return body

if __name__ == '__main__':
    app = connexion.AioHttpApp(
        __name__,
        port=8080,
        specification_dir='.',
        options={'swagger_ui': True}
    )
    app.add_api('schema.yaml')
    app.run()
