import collections
from copy import deepcopy

from jsonschema import RefResolver
from jsonschema.exceptions import RefResolutionError  # noqa
from openapi_spec_validator.handlers import UrlHandler

from .utils import deep_get

default_handlers = {
    'http': UrlHandler('http'),
    'https': UrlHandler('https'),
    'file': UrlHandler('file'),
}


def resolve_refs(spec, store=None, handlers=None):
    """
    Resolve JSON references like {"$ref": <some URI>} in a spec.
    Optionally takes a store, which is a mapping from reference URLs to a
    dereferenced objects. Prepopulating the store can avoid network calls.
    """
    spec = deepcopy(spec)
    store = store or {}
    handlers = handlers or default_handlers
    resolver = RefResolver('', spec, store, handlers=handlers)

    def _do_resolve(node):
        if isinstance(node, collections.Mapping) and '$ref' in node:
            path = node['$ref'][2:].split("/")
            try:
                # resolve known references
                node.update(deep_get(spec, path))
                del node['$ref']
                return node
            except KeyError:
                # resolve external references
                with resolver.resolving(node['$ref']) as resolved:
                    return resolved
        elif isinstance(node, collections.Mapping):
            for k, v in node.items():
                node[k] = _do_resolve(v)
        elif isinstance(node, (list, tuple)):
            for i, _ in enumerate(node):
                node[i] = _do_resolve(node[i])
        return node

    res = _do_resolve(spec)
    return res
