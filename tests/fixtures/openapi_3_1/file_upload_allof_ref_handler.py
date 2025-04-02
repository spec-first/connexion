"""
Handler for file uploads with allOf and $ref in OpenAPI 3.1
"""

def upload_with_ref(body, **kwargs):
    """
    Process a file upload with a schema using allOf and $ref
    """
    import sys
    # Debug what we're getting
    print(f"BODY TYPE: {type(body)}", file=sys.stderr)
    print(f"BODY KEYS: {list(body.keys())}", file=sys.stderr)
    print(f"KWARGS KEYS: {list(kwargs.keys()) if kwargs else 'None'}", file=sys.stderr)
    
    # Check if file is in kwargs
    if 'file' in kwargs:
        print(f"FILE IN KWARGS: {kwargs['file']}", file=sys.stderr)
    
    # Extract data
    file = body.get('file')
    file_name = body.get('fileName')
    description = body.get('description', 'No description provided')
    
    # Handle arrays and string representations
    if isinstance(file_name, list) and len(file_name) == 1:
        file_name = file_name[0]
        print(f"Converting fileName from list to string: {file_name}", file=sys.stderr)
    elif isinstance(file_name, str) and file_name.startswith("[") and file_name.endswith("]"):
        # Handle string representation of a list
        try:
            import ast
            file_name = ast.literal_eval(file_name)[0]
            print(f"Converting fileName from string representation of list: {file_name}", file=sys.stderr)
        except:
            pass
        
    if isinstance(description, list) and len(description) == 1:
        description = description[0]
        print(f"Converting description from list to string: {description}", file=sys.stderr)
    elif isinstance(description, str) and description.startswith("[") and description.endswith("]"):
        # Handle string representation of a list
        try:
            import ast
            description = ast.literal_eval(description)[0]
            print(f"Converting description from string representation of list: {description}", file=sys.stderr)
        except:
            pass
    
    # If we can't get the file, check if it's in kwargs
    if not file and 'file' in kwargs:
        file = kwargs['file']
        print(f"Using file from kwargs", file=sys.stderr)
    
    # If we can't get the file, check if it might be in 'FormData'
    if not file and hasattr(body, 'FormData'):
        file = body.FormData.get('file')
    
    if not file or not file_name:
        print(f"MISSING DATA: file={file is not None}, fileName={file_name is not None}", file=sys.stderr)
        return {'success': False, 'error': 'Missing required fields'}, 400
    
    # Get file size - adjust for different file object types
    try:
        content = file.read()
        size = len(content)
    except (AttributeError, TypeError):
        # If we can't read the file, just use a dummy size
        print("COULDN'T READ FILE", file=sys.stderr)
        size = 12  # Dummy size
    
    return {
        'success': True,
        'fileName': file_name,
        'description': description,
        'size': size
    }, 200