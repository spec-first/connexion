import datetime

from flask import request
from flask.views import MethodView

from connexion import NoContent


class PetsView(MethodView):
    """ Create Pets service
    """
    method_decorators = []
    pets = {}

    def post(self):
      body= request.json
      name = body.get("name")
      tag = body.get("tag")
      count = len(self.pets)
      pet = {}
      pet['id'] = count + 1
      pet["tag"] = tag
      pet["name"] = name
      pet['last_updated'] = datetime.datetime.now()
      self.pets[pet['id']] = pet
      return pet, 201

    def put(self, petId):
      body = request.json
      # id_ = body["id"]
      name = body["name"]
      tag = body.get("tag")
      print(type(petId))
      id_ = int(petId)
      pet = self.pets.get(petId, {"id": petId})
      pet["name"] = name
      pet["tag"] = tag
      pet['last_updated'] = datetime.datetime.now()
      self.pets[petId] = pet
      return self.pets[petId], 201

    def delete(self, petId):
      id_ = int(petId)
      if self.pets.get(petId) is None:
          return NoContent, 404
      del self.pets[petId]
      return NoContent, 204

    def get(self, petId):
      id_ = int(petId)
      if self.pets.get(id_) is None:
          return NoContent, 404
      return self.pets[id_]

    def search(self, limit=100):
      # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
      return list(self.pets.values())[0:limit]
