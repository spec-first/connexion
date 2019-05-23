from __future__ import absolute_import

import connexion
from collections import OrderedDict
import flask
import uuid

API_APP = None

_INTERNAL_CACHE = None


def setupApp():
    global API_APP
    API_APP = connexion.App(__name__, specification_dir='openapi_schemas')
    API_APP.add_api('post_and_get.yaml', validate_responses=True)


def cleanSite():
    global _INTERNAL_CACHE
    _INTERNAL_CACHE = OrderedDict()


def get_trans_list():
    return flask.jsonify({'transactions': list(_INTERNAL_CACHE.values())}), 200


def post_trans_record():
    request_obj = flask.request.json
    request_obj['transaction']['id'] = uuid.uuid4()
    _INTERNAL_CACHE[request_obj['transaction']['id']] = request_obj
    return flask.jsonify(request_obj), 201


def get_trans_record(transactionId):
    if transactionId not in _INTERNAL_CACHE:
        return flask.jsonify({'error': {'message': 'Resource not found'}}), 404
    return flask.jsonify(_INTERNAL_CACHE[transactionId])