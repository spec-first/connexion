from collections import namedtuple

_ConnexionRequest = namedtuple('SwaggerRequest', [
    'url', 'method', 'path_params', 'query', 'headers',
    'form', 'body', 'json', 'files', 'context'
])


class ConnexionRequest(_ConnexionRequest):

    def __new__(cls, url, method, path_params=None, query=None, headers=None,
                form=None, body=None, json=None, files=None, context=None):
        return _ConnexionRequest.__new__(
            cls, url, method,
            path_params=path_params or {},
            query=query or {},
            headers=headers or {},
            form=form or {},
            body=body,
            json=json,
            files=files,
            context=context or {}
        )
