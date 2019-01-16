from flask.views import MethodView


class Example_methodView(MethodView):
    def get(self):
      return "yeah"
    def search(self):
      return ""
    def api_list(self):
      return ""
    def post_greeting(self):
      return ""
    def post(self):
      return ""
