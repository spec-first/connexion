from connexion import NoContent
import time
from rfc3339 import rfc3339

pets = {}


def post(pet):
    count = len(pets)
    pet['id'] = count + 1
    pet['registered'] = rfc3339(time.time())
    pets[pet['id']] = pet
    return pet, 201


def put(id, pet):
    id = int(id)
    if pets.get(id) is None:
        return NoContent, 404
    pets[id] = pet

    return pets[id]


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

    return pets[id]


def search():
    return pets.values()
