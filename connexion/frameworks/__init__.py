

class Framework:
    '''Generic interface for framework implementations

    assumptions about request object:

    * headers: dict (case insensitive or not)
    * data: Python object (e.g. JSON request body)
    * args:
    * form:
    * files:
    '''
    def __init__(self, base_url):
        raise NotImplementedError()

    def register_operation(self, method, path, operation):
        raise NotImplementedError()

    def register_swagger_json(self):
        raise NotImplementedError()

    def register_swagger_ui():
        raise NotImplementedError()
