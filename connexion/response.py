from collections import namedtuple

_ConnexionResponse = namedtuple('SwaggerRequest', [
    'mimetype', 'content_type', 'status_code', 'body', 'headers'
])


class ConnexionResponse(_ConnexionResponse):

    def __new__(cls, status_code=200, mimetype=None, content_type=None, body=None, headers=None):
        return _ConnexionResponse.__new__(
            cls, mimetype,
            content_type,
            status_code,
            body=body,
            headers=headers or {}
        )
