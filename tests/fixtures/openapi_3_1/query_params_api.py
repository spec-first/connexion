"""
Test API implementation for complex query parameters
"""

def get_with_oneof(limit=None):
    """Handle endpoint with oneOf in query parameter"""
    return {"limit": limit}, 200


def get_with_anyof(filter=None):
    """Handle endpoint with anyOf in query parameter"""
    return {"filter": filter}, 200


def get_with_allof(range=None):
    """Handle endpoint with allOf in query parameter"""
    return {"range": range}, 200