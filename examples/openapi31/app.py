#!/usr/bin/env python3
"""
OpenAPI 3.1 example application
"""

import connexion
from connexion.exceptions import OAuthProblem

# Our "database" of users
USERS = {
    1: {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "metadata": {}},
    2: {"id": 2, "username": "jane_smith", "email": "jane@example.com", "status": "inactive", "metadata": {"location": "New York"}},
}
NEXT_ID = 3


def hello_world():
    """Return a friendly greeting."""
    return {"message": "Hello, world! Welcome to the OpenAPI 3.1 example."}


def get_users():
    """Return the list of all users."""
    return list(USERS.values())


def get_user(user_id):
    """Return a user by ID."""
    if user_id not in USERS:
        return {"error": "User not found"}, 404
    return USERS[user_id]


def create_user(body):
    """Create a new user."""
    global NEXT_ID
    new_user = {
        "id": NEXT_ID,
        "username": body["username"],
        "email": body["email"],
        "status": body.get("status", "active"),
        "metadata": body.get("metadata", {})
    }
    USERS[NEXT_ID] = new_user
    NEXT_ID += 1
    return new_user, 201


if __name__ == "__main__":
    app = connexion.App(__name__, specification_dir="spec/")
    app.add_api("openapi.yaml")
    app.run(port=8090)