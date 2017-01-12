

class Framework:
    '''Generic interface for framework implementations'''

    def register_operation(self, method, path, operation):
        raise NotImplementedError()

    def register_swagger_json(self):
        raise NotImplementedError()

    def register_swagger_ui():
        raise NotImplementedError()
