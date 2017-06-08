
class ConnexionRequest(object):
    def __init__(self,
                 url,
                 method,
                 path_params=None,
                 query=None,
                 headers=None,
                 form=None,
                 body=None,
                 json=None,
                 files=None,
                 context=None):
        self.url = url
        self.method = method
        self.path_params = path_params or {}
        self.query = query or {}
        self.headers = headers or {}
        self.form = form or {}
        self.body = body
        self.json = json
        self.files = files
        self.context = context or {}


class ConnexionResponse(object):
    def __init__(self,
                 status_code=200,
                 mimetype=None,
                 content_type=None,
                 body=None,
                 headers=None):
        self.status_code = status_code
        self.mimetype = mimetype
        self.content_type = content_type
        self.body = body
        self.headers = ConnexionHeaders(headers)


class ConnexionHeaders(object):
    def __init__(self, headers):
        self.headers = headers or list()

    def getlist(self, name):
        """
        Given a header name, return the list of values that was sent with that
        name.
        """
        return [v
                for n, v in self.headers
                if n == name]

    def getfirst(self, name, defaultvalue=None):
        """
        Given a header name, return the first value that was sent with that
        name.  If the header name is not found, return `defaultvalue`.
        """
        for n, v in self.headers:
            if n == name:
                return v
        return defaultvalue

    def __iter__(self):
        return self.headers.__iter__()
