from connexion import NoContent
from flask import Response
import time
from rfc3339 import rfc3339
import json

pets = {}


def post(pet):
    count = len(pets)
    pet['id'] = count + 1
    pet['registered'] = rfc3339(time.time())
    pets[pet['id']] = pet
    return Response(json.dumps(pet), status=201, mimetype='application/json')


def put(id, pet):
    id = int(id)
    if pets.get(id) is None:
        return NoContent, 404
    pets[id] = pet

    return Response(json.dumps(pets[id]), status=200, mimetype='application/json')


def delete(id):
    id = int(id)
    if pets.get(id) is None:
        return NoContent, 404
    del pets[id]
    return NoContent, 204


def get(id):
    id = int(id)
    if pets.get(id) is None:
        return NoContent, 404

    return Response(json.dumps(pets[id]), status=200, mimetype='application/json')


def search():
    return Response(json.dumps(pets.values()), status=200, mimetype='application/json')
