#!/usr/bin/env python3
"""
OpenAPI 3.1 example application

This example demonstrates various OpenAPI 3.1 features:
- JSON Schema 2020-12 alignment
- Type arrays for nullability
- Webhooks
- Server variables
- Advanced validation features
"""

import connexion
from connexion.exceptions import OAuthProblem

# Our "database" of users
USERS = {
    1: {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "metadata": {"location": "New York"}},
    2: {"id": 2, "username": "jane_smith", "email": "jane@example.com", "status": "inactive", "metadata": {}},
}
NEXT_ID = 3

# Keep track of webhook calls
WEBHOOK_CALLS = []


def hello_world():
    """Return a friendly greeting."""
    return {"message": "Hello, world! Welcome to the OpenAPI 3.1 example."}


def get_users():
    """Return the list of all users."""
    return list(USERS.values())


def get_user(user_id):
    """Return a user by ID."""
    if user_id not in USERS:
        return {"code": 404, "message": "User not found"}, 404
    return USERS[user_id]


def create_user(body):
    """Create a new user."""
    global NEXT_ID
    
    # Validate metadata if present
    metadata = body.get("metadata", {})
    if metadata and not isinstance(metadata, dict):
        return {"code": 400, "message": "Metadata must be an object"}, 400

    # Check for unevaluated properties in metadata
    for key in metadata:
        if key not in ["location", "preferences"]:
            return {"code": 400, "message": f"Unknown metadata property: {key}"}, 400

    new_user = {
        "id": NEXT_ID,
        "username": body["username"],
        "email": body["email"],
        "status": body.get("status", "active"),
        "metadata": metadata
    }
    USERS[NEXT_ID] = new_user
    NEXT_ID += 1
    
    # Simulate webhook call
    trigger_user_created_webhook(new_user)
    
    return new_user, 201


def get_webhook_calls():
    """Return the list of webhook calls."""
    return WEBHOOK_CALLS


def process_user_webhook(body):
    """Process an incoming webhook."""
    WEBHOOK_CALLS.append({
        "type": "user_webhook",
        "payload": body
    })
    return {"message": "Webhook processed successfully"}


def trigger_user_created_webhook(user):
    """Simulate triggering the webhook when a user is created."""
    WEBHOOK_CALLS.append({
        "type": "user_created",
        "payload": user
    })


if __name__ == "__main__":
    app = connexion.App(__name__, specification_dir="spec/")
    app.add_api("openapi.yaml")
    app.run(port=8090)