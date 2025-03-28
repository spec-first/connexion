"""
Test API implementation for advanced OpenAPI 3.1 features
"""

# In-memory storage for pets
PETS = [
    {"id": 1, "name": "Fluffy", "species": "cat", "age": 3},
    {"id": 2, "name": "Buddy", "species": "dog", "age": 5},
    {"id": 3, "name": None, "species": "bird", "age": 1},  # Test nullable name
]

# Track webhook calls
WEBHOOK_CALLS = []


def get_pets():
    """Get all pets"""
    return PETS, 200


def get_pet(pet_id):
    """Get a pet by ID"""
    for pet in PETS:
        if pet["id"] == pet_id:
            return pet, 200
    return {"code": 404, "message": "Pet not found"}, 404


def add_pet(body):
    """Add a new pet"""
    # Validate required fields are present
    if "id" not in body or "species" not in body:
        return {"code": 400, "message": "Missing required fields"}, 400
    
    # Validate species enum
    if body["species"] not in ["dog", "cat", "bird"]:
        return {"code": 400, "message": "Invalid species"}, 400
    
    # Validate age is greater than 0
    if "age" in body and body["age"] <= 0:
        return {"code": 400, "message": "Age must be greater than 0"}, 400
    
    PETS.append(body)
    return body, 201


def add_pet_with_metadata(body):
    """Add a new pet with metadata"""
    # Basic validation
    if "id" not in body or "species" not in body:
        return {"code": 400, "message": "Missing required fields"}, 400
    
    # Validate species enum
    if body["species"] not in ["dog", "cat", "bird"]:
        return {"code": 400, "message": "Invalid species"}, 400
    
    # Validate metadata structure
    if "metadata" in body:
        # Only allow known properties in metadata
        allowed_keys = ["color", "weight"]
        for key in body["metadata"]:
            if key not in allowed_keys:
                return {"code": 400, "message": f"Unknown metadata property: {key}"}, 400
    
    PETS.append(body)
    return body, 201


def process_new_pet_webhook(body):
    """Process a webhook notification for a new pet"""
    WEBHOOK_CALLS.append(body)
    return {"message": "Webhook processed successfully"}, 200