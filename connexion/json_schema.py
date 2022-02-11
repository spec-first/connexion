"""
Module containing all code related to json schema validation.
"""

import typing as t
from collections.abc import Mapping
from copy import deepcopy

from jsonschema import Draft4Validator, RefResolver
from jsonschema.exceptions import RefResolutionError, ValidationError  # noqa
from jsonschema.validators import extend
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
        if isinstance(node, Mapping) and '$ref' in node:
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
        elif isinstance(node, Mapping):
            for k, v in node.items():
                node[k] = _do_resolve(v)
        elif isinstance(node, (list, tuple)):
            for i, _ in enumerate(node):
                node[i] = _do_resolve(node[i])
        return node

    res = _do_resolve(spec)
    return res


def allow_nullable(validation_fn: t.Callable) -> t.Callable:
    """Extend an existing validation function, so it allows nullable values to be null."""

    def nullable_validation_fn(validator, to_validate, instance, schema):
        if instance is None and (schema.get('x-nullable') is True or schema.get('nullable')):
            return

        yield from validation_fn(validator, to_validate, instance, schema)

    return nullable_validation_fn


def validate_required(validator, required, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for prop in required:
        if prop not in instance:
            properties = schema.get('properties')
            if properties is not None:
                subschema = properties.get(prop)
                if subschema is not None:
                    if 'readOnly' in validator.VALIDATORS and subschema.get('readOnly'):
                        continue
                    if 'writeOnly' in validator.VALIDATORS and subschema.get('writeOnly'):
                        continue
                    if 'x-writeOnly' in validator.VALIDATORS and subschema.get('x-writeOnly') is True:
                        continue
            yield ValidationError("%r is a required property" % prop)


def validate_readOnly(validator, ro, instance, schema):
    yield ValidationError("Property is read-only")


def validate_writeOnly(validator, wo, instance, schema):
    yield ValidationError("Property is write-only")


Draft4RequestValidator = extend(Draft4Validator, {
                                'type': allow_nullable(Draft4Validator.VALIDATORS['type']),
                                'enum': allow_nullable(Draft4Validator.VALIDATORS['enum']),
                                'required': validate_required,
                                'readOnly': validate_readOnly})

Draft4ResponseValidator = extend(Draft4Validator, {
                                 'type': allow_nullable(Draft4Validator.VALIDATORS['type']),
                                 'enum': allow_nullable(Draft4Validator.VALIDATORS['enum']),
                                 'required': validate_required,
                                 'writeOnly': validate_writeOnly,
                                 'x-writeOnly': validate_writeOnly})
