"""
Test API implementation for OpenAPI 3.1 support
"""

# In-memory storage for pets
PETS = [
    {"id": 1, "name": "Fluffy", "tag": "cat"},
    {"id": 2, "name": "Buddy", "tag": "dog"},
]


def get_pets():
    """Get all pets"""
    return PETS, 200


def get_pet(pet_id):
    """Get a pet by ID"""
    for pet in PETS:
        if pet["id"] == pet_id:
            return pet, 200
    return {"error": "Pet not found"}, 404


def add_pet(body):
    """Add a new pet"""
    PETS.append(body)
    return body, 201


def get_secure():
    """Handle secure endpoint with OAuth2 or mutual TLS"""
    return {"message": "Authenticated successfully"}, 200
