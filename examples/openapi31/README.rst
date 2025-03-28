====================
OpenAPI 3.1 Example
====================

This example demonstrates the OpenAPI 3.1 support in Connexion.

Key features showcased:
- JSON Schema 2020-12 support (specified via jsonSchemaDialect)
- Updated OpenAPI 3.1 schema validation
- Compatibility with the new OpenAPI 3.1 structure

Running:

.. code-block:: bash

    $ python app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.

API Endpoints:
- GET /: Returns a greeting message
- GET /users: List all users
- POST /users: Create a new user
- GET /users/{user_id}: Get a specific user by ID

Try out the API using curl:

.. code-block:: bash

    $ curl -X GET http://localhost:8080/
    {"message": "Hello, world! Welcome to the OpenAPI 3.1 example."}

    $ curl -X GET http://localhost:8080/users
    [{"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "metadata": {}}, ...]

    $ curl -X POST -H "Content-Type: application/json" -d '{"username": "new_user", "email": "new@example.com"}' http://localhost:8080/users
    {"id": 3, "username": "new_user", "email": "new@example.com", "status": "active", "metadata": {}}

    $ curl -X GET http://localhost:8080/users/1
    {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "metadata": {}}