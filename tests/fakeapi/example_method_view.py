from flask.views import MethodView


class ExampleMethodView(MethodView):
    mycontent="demonstrate return from MethodView class"
    def get(self):
      return self.mycontent
    def search(self):
      return self.mycontent
    def api_list(self):
      return self.mycontent
    def post_greeting(self):
      return self.mycontent
    def post(self):
      return self.mycontent
