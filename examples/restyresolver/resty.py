#!/usr/bin/env python
import connexion
import logging
from connexion.resolver import RestyResolver

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    app = connexion.App(__name__)
    app.add_api('resty-api.yaml', arguments={'title': 'RestyResolver Example'}, resolver=RestyResolver('api'))
    app.run(port=9090)
