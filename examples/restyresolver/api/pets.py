import datetime

from connexion import NoContent

pets = {}


def post(body):
    name = body.get("name")
    tag = body.get("tag")
    count = len(pets)
    pet = {}
    pet["id"] = count + 1
    pet["tag"] = tag
    pet["name"] = name
    pet["last_updated"] = datetime.datetime.now()
    pets[pet["id"]] = pet
    return pet, 201


def put(body):
    id_ = body["id"]
    name = body["name"]
    tag = body.get("tag")
    id_ = int(id_)
    pet = pets.get(id_, {"id": id_})
    pet["name"] = name
    pet["tag"] = tag
    pet["last_updated"] = datetime.datetime.now()
    pets[id_] = pet
    return pets[id_]


def delete(id_):
    id_ = int(id_)
    if pets.get(id_) is None:
        return NoContent, 404
    del pets[id_]
    return NoContent, 204


def get(petId):
    id_ = int(petId)
    if pets.get(id_) is None:
        return NoContent, 404
    return pets[id_]


def search(limit=100):
    # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
    return list(pets.values())[0:limit]
