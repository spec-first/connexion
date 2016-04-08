import datetime

from connexion import NoContent

pets = {}


def post(pet):
    count = len(pets)
    pet['id'] = count + 1
    pet['registered'] = datetime.datetime.now()
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
    # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
    return list(pets.values())
