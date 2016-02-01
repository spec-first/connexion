#!/usr/bin/env python2.7
import connexion
import logging
from connexion.resolver import RestyResolver
logging.basicConfig(level=logging.INFO)
app = connexion.App(__name__)
application = app.app

if __name__ == '__main__':
    app = connexion.App(__name__, 9090)
    app.add_api('resty-api.yaml', arguments={'title': 'RestyResolver Example'}, resolver=RestyResolver('api'))
    app.run()
