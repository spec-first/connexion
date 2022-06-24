from flask.views import MethodView


class PetsView(MethodView):

    mycontent="demonstrate return from MethodView class"

    def get(self, **kwargs):
        kwargs.update({
            "method": "get"
        })
        return kwargs

    def search(self):
        return "search"

    def post(self, **kwargs):
        kwargs.update({
            "method": "post"
        })
        return kwargs

    def put(self, *args, **kwargs):
        kwargs.update({
            "method": "put"
        })
        return kwargs

    # Test that operation_id can still override resolver

    def api_list(self):
        return "api_list"

    def post_greeting(self):
        return "post_greeting"
