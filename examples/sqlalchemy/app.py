import logging
from datetime import datetime, timezone

import connexion
import orm
from connexion import NoContent


def get_pets(limit, animal_type=None):
    with db_session_factory() as db_session:
        q = db_session.query(orm.Pet)
        if animal_type:
            q = q.filter(orm.Pet.animal_type == animal_type)
        return [p.dump() for p in q][:limit]


def get_pet(pet_id):
    with db_session_factory() as db_session:
        pet = db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).one_or_none()
        return pet.dump() if pet is not None else ("Not found", 404)


def put_pet(pet_id, pet):
    with db_session_factory() as db_session:
        p = db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).one_or_none()
        pet["id"] = pet_id
        if p is not None:
            logging.info("Updating pet %s..", pet_id)
            p.update(**pet)
        else:
            logging.info("Creating pet %s..", pet_id)
            pet["created"] = datetime.now(timezone.utc)
            db_session.add(orm.Pet(**pet))
        db_session.commit()
        return NoContent, (200 if p is not None else 201)


def delete_pet(pet_id):
    with db_session_factory() as db_session:
        pet = db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).one_or_none()
        if pet is not None:
            logging.info("Deleting pet %s..", pet_id)
            db_session.delete(pet)
            db_session.commit()
            return NoContent, 204
        else:
            return NoContent, 404


logging.basicConfig(level=logging.INFO)
db_session_factory = orm.init_db()
pets = {
    1: {"name": "Aldo", "animal_type": "cat"},
    2: {"name": "Bailey", "animal_type": "dog"},
    3: {"name": "Hugo", "animal_type": "cat"},
}
for id_, pet in pets.items():
    put_pet(id_, pet)
app = connexion.FlaskApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml")
app.add_api("swagger.yaml")


if __name__ == "__main__":
    app.run(port=8080, reload=False)
