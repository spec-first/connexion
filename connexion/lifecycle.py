"""
This module defines interfaces for requests and responses used in Connexion for authentication,
validation, serialization, etc.
"""


class ConnexionRequest:
    """Connexion interface for a request."""
    def __init__(self,
                 url,
                 method,
                 path_params=None,
                 query=None,
                 headers=None,
                 form=None,
                 body=None,
                 json_getter=None,
                 files=None,
                 context=None,
                 cookies=None):
        self.url = url
        self.method = method
        self.path_params = path_params or {}
        self.query = query or {}
        self.headers = headers or {}
        self.form = form or {}
        self.body = body
        self.json_getter = json_getter
        self.files = files
        self.context = context if context is not None else {}
        self.cookies = cookies or {}

    @property
    def json(self):
        if not hasattr(self, '_json'):
            self._json = self.json_getter()
        return self._json


class ConnexionResponse:
    """Connexion interface for a response."""
    def __init__(self,
                 status_code=200,
                 mimetype=None,
                 content_type=None,
                 body=None,
                 headers=None,
                 is_streamed=False):
        self.status_code = status_code
        self.mimetype = mimetype
        self.content_type = content_type
        self.body = body
        self.headers = headers or {}
        self.is_streamed = is_streamed
