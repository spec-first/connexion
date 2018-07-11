import datetime

from connexion import NoContent

pets = {}


def post(body):
    name = body.get("name")
    tag = body.get("tag")
    count = len(pets)
    pet = {}
    pet['id'] = count + 1
    pet["tag"] = tag
    pet["name"] = name
    pet['last_updated'] = datetime.datetime.now()
    pets[pet['id']] = pet
    return pet, 201


def put(body):
    id = body["id"]
    name = body["name"]
    tag = body.get("tag")
    id = int(id)
    pet = pets.get(id, {"id": id})
    pet["name"] = name
    pet["tag"] = tag
    pet['last_updated'] = datetime.datetime.now()
    pets[id] = pet
    return pets[id]


def delete(id):
    id = int(id)
    if pets.get(id) is None:
        return NoContent, 404
    del pets[id]
    return NoContent, 204


def get(petId):
    id = int(petId)
    if pets.get(id) is None:
        return NoContent, 404
    return pets[id]


def search(limit=100):
    # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
    return list(pets.values())[0:limit]
