class PetsView:

    mycontent = "demonstrate return from MethodView class"

    def get(self, **kwargs):
        if kwargs:
            kwargs.update({"name": "get"})
            return kwargs
        else:
            return [{"name": "get"}]

    def search(self):
        return [{"name": "search"}]

    def post(self, **kwargs):
        kwargs.update({"name": "post"})
        return kwargs, 201

    def put(self, *args, **kwargs):
        kwargs.update({"name": "put"})
        return kwargs, 201

    def delete(self, **kwargs):
        return 201

    # Test that operation_id can still override resolver

    def api_list(self):
        return "api_list"

    def post_greeting(self):
        return "post_greeting"
