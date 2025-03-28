====================
OpenAPI 3.1 Example
====================

This example demonstrates the OpenAPI 3.1 support in Connexion.

Key features showcased:
- JSON Schema 2020-12 support (specified via jsonSchemaDialect)
- Type arrays for nullability (e.g., ``type: ["string", "null"]`` instead of nullable property)
- Webhooks support (new in OpenAPI 3.1)
- Server variable templates (e.g., ``https://{environment}.example.com``)
- New validation features like unevaluatedProperties
- Enhanced examples

Running:

.. code-block:: bash

    $ python app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.

API Endpoints:
- GET /: Returns a greeting message
- GET /users: List all users
- POST /users: Create a new user
- GET /users/{user_id}: Get a specific user by ID
- GET /webhook-calls: Get a list of recorded webhook calls

Try out the API using curl:

.. code-block:: bash

    $ curl -X GET http://localhost:8080/
    {"message": "Hello, world! Welcome to the OpenAPI 3.1 example."}

    $ curl -X GET http://localhost:8080/users
    [{"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "metadata": {"location": "New York"}}, ...]

    # Create a user with valid metadata
    $ curl -X POST -H "Content-Type: application/json" -d '{"username": "new_user", "email": "new@example.com", "metadata": {"location": "San Francisco"}}' http://localhost:8080/users
    {"id": 3, "username": "new_user", "email": "new@example.com", "status": "active", "metadata": {"location": "San Francisco"}}

    # This will fail due to unevaluatedProperties validation (unknown property in metadata)
    $ curl -X POST -H "Content-Type: application/json" -d '{"username": "invalid", "email": "invalid@example.com", "metadata": {"unknown": "value"}}' http://localhost:8080/users
    {"code": 400, "message": "Unknown metadata property: unknown"}

    # Get a specific user
    $ curl -X GET http://localhost:8080/users/1
    {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "metadata": {"location": "New York"}}

    # Check webhook calls (simulated within the application)
    $ curl -X GET http://localhost:8080/webhook-calls
    [{"type": "user_created", "payload": {...}}]