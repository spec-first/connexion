from connexion.resolver import Resolution, Resolver
from flask import Response, request
import requests
import json

# urljoin for 2 and 3
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from .utils import partial

CHUNK_SIZE = 1024


def proxy(base_url="", path="", *_):
    """
    Proxy connections to the API
    """
    url = urljoin(base_url, path)
    params = {}
    args = dict(request.args.items())
    params.update(args)
    headers = {
        "Content-Type": "application/json",
        "Authorization": request.headers.get("Authorization", "")
    }
    response = requests.get(
        url,
        params=params,
        headers=headers,
        stream=True
    )
    if response.status_code != 200:
        err = {"error": "There was an error in the API."}
        try:
            err.update(response.json())
        except ValueError:
            # No JSON could be decoded
            pass  # no detail to add
        return Response(response=json.dumps(err),
                        status=response.status_code, mimetype='application/json')

    def generate():
        for chunk in response.iter_content(CHUNK_SIZE):
            yield chunk

    ret = Response(
        response=generate(),
        status=200,
        mimetype='application/json'
    )
    return ret


class ProxyResolver(Resolver):

    def __init__(self, base_url, override={}):
        self._operation_id_counter = 1
        self.base_url = base_url
        self.override = override

    def resolve(self, operation):
        """
        Proxy operation resolver
        :type operation: connexion.operation.Operation
        """
        operation_id = self.resolve_operation_id(operation)
        if not operation_id:
            # just generate an unique operation ID
            operation_id = 'fake-{}'.format(self._operation_id_counter)
            self._operation_id_counter += 1

        func = partial(proxy, base_url=self.base_url, path=operation.path)
        return Resolution(func, operation_id)
