"""
Test API implementation for file uploads with allOf schema
"""


def upload_simple(body=None):
    """Handle simple file upload"""
    # Non-async handler for Connexion to properly handle
    if body is None:
        return {"error": "Body is None"}, 400

    file = body.get("file")
    name = body.get("name")

    if not file or not name:
        return {"error": "Missing required fields"}, 400

    return {
        "filename": file.filename,
        "size": len(file.read()),
        "content_type": file.content_type,
        "name": name,
    }, 200


def upload_with_allof(body=None):
    """Handle file upload with allOf schema"""
    # Non-async handler for Connexion to properly handle
    if body is None:
        return {"error": "Body is None"}, 400

    file = body.get("file")
    name = body.get("name")

    # Handle case where name is a list but should be a string
    if isinstance(name, list) and len(name) == 1:
        name = name[0]
    # Handle case where name is a string but formatted as list
    elif isinstance(name, str) and name.startswith("[") and name.endswith("]"):
        name = name.strip("[]").strip("'\"")

    if not file or not name:
        return {"error": "Missing required fields"}, 400

    return {
        "filename": file.filename,
        "size": len(file.read()),
        "content_type": file.content_type,
        "name": name,
    }, 200
