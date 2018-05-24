#!/usr/bin/env python3
import datetime
import logging

import connexion
from connexion import NoContent

import orm

db_session = None


def get_pets(limit=100, animal_type=None):
    q = db_session.query(orm.Pet)
    if animal_type:
        q = q.filter(orm.Pet.animal_type == animal_type)
    return [p.dump() for p in q][:limit]


def get_pet(pet_id):
    pet = db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).one_or_none()
    return pet.dump() if pet is not None else ('Not found', 404)


def put_pet(pet_id, body):
    p = db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).one_or_none()
    body['id'] = pet_id
    if p is not None:
        logging.info('Updating pet %s..', pet_id)
        p.update(**body)
    else:
        logging.info('Creating pet %s..', pet_id)
        body['created'] = datetime.datetime.utcnow()
        db_session.add(orm.Pet(**body))
    db_session.commit()
    return NoContent, (200 if p is not None else 201)


def delete_pet(pet_id):
    pet = db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).one_or_none()
    if pet is not None:
        logging.info('Deleting pet %s..', pet_id)
        db_session.query(orm.Pet).filter(orm.Pet.id == pet_id).delete()
        db_session.commit()
        return NoContent, 204
    else:
        return NoContent, 404

logging.basicConfig(level=logging.INFO)
db_session = orm.init_db('sqlite:///:memory:')
app = connexion.FlaskApp(__name__)
app.add_api('swagger.yaml')

application = app.app


@application.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == '__main__':
    app.run(port=8081,  use_reloader=False, threaded=False)
