"""
Module containing all code related to json schema validation.
"""

import contextlib
import io
import json
import os
import typing as t
import urllib.parse
import urllib.request
from collections.abc import Mapping
from copy import deepcopy

import requests
import yaml
from jsonschema import Draft4Validator
from jsonschema.exceptions import ValidationError
from jsonschema.validators import extend
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4

from .utils import deep_get


class ExtendedSafeLoader(yaml.SafeLoader):
    """Extends the yaml SafeLoader to coerce all keys to string so the result is valid json."""

    def __init__(self, stream):
        self.original_construct_mapping = self.construct_mapping
        self.construct_mapping = self.extended_construct_mapping
        super().__init__(stream)

    def extended_construct_mapping(self, node, deep=False):
        data = self.original_construct_mapping(node, deep)
        return {str(key): data[key] for key in data}


class FileHandler:
    """Handler to resolve file refs."""

    def __call__(self, uri):
        filepath = self._uri_to_path(uri)
        with open(filepath) as fh:
            return yaml.load(fh, ExtendedSafeLoader)

    @staticmethod
    def _uri_to_path(uri):
        parsed = urllib.parse.urlparse(uri)
        host = "{0}{0}{mnt}{0}".format(os.path.sep, mnt=parsed.netloc)
        return os.path.abspath(
            os.path.join(host, urllib.request.url2pathname(parsed.path))
        )


class URLHandler:
    """Handler to resolve url refs."""

    def __call__(self, uri):
        response = requests.get(uri)
        response.raise_for_status()

        data = io.StringIO(response.text)
        with contextlib.closing(data) as fh:
            return yaml.load(fh, ExtendedSafeLoader)


def resource_from_spec(spec: t.Dict[str, t.Any]) -> Resource:
    """Create a `referencing.Resource` from a schema specification."""
    return Resource.from_contents(spec, default_specification=DRAFT4)


def retrieve(uri: str) -> Resource:
    """Retrieve a resource from a URI.

    This function is passed to the `referencing.Registry`,
    which calls it whenever a URI not present in the registry is accessed."""
    parsed = urllib.parse.urlsplit(uri)
    if parsed.scheme in ("http", "https"):
        content = URLHandler()(uri)
    elif parsed.scheme in ("file", ""):
        content = FileHandler()(uri)
    else:  # pragma: no cover
        # Default branch from jsonschema.RefResolver.resolve_remote()
        # for backwards compatibility.
        with urllib.request.urlopen(uri) as url:
            content = json.loads(url.read().decode("utf-8"))
    return resource_from_spec(content)


def resolve_refs(spec, store=None, base_uri=""):
    """
    Resolve JSON references like {"$ref": <some URI>} in a spec.
    Optionally takes a store, which is a mapping from reference URLs to a
    dereferenced objects. Prepopulating the store can avoid network calls.
    """
    spec = deepcopy(spec)
    store = store or {}
    registry = Registry(retrieve=retrieve).with_resources(
        (
            (base_uri, resource_from_spec(spec)),
            *((key, resource_from_spec(value)) for key, value in store.items()),
        )
    )

    def _do_resolve(node, resolver, _expanding=()):
        if isinstance(node, Mapping) and "$ref" in node:
            ref = node["$ref"]
            if ref in _expanding:
                # Recursive reference (e.g. a schema that references itself
                # through its own properties). Inlining it would build a
                # cyclic object graph, which makes validation loop forever
                # and breaks anything that walks the resolved spec. Leave
                # the reference in place: consumers that attach the
                # components section (e.g. request/response body validation)
                # resolve it against the document, following the instance
                # depth instead of looping over the schema.
                return node
            path = ref[2:].split("/")
            try:
                # resolve known references
                retrieved = deep_get(spec, path)
            except KeyError:
                # resolve external references
                resolved = resolver.lookup(ref)
                return _do_resolve(
                    deepcopy(resolved.contents), resolved.resolver, _expanding + (ref,)
                )
            # Copy before inlining: updating the node with the retrieved
            # object as-is shares its sub-objects with the spec, so a
            # later resolution step mutating the shared object turns a
            # recursive reference into a cycle in the resolved spec.
            # Resolve nested references inside the copy as well, so an
            # inlined schema does not depend on the components section
            # being walked later.
            resolved_target = _do_resolve(
                deepcopy(retrieved), resolver, _expanding + (ref,)
            )
            if isinstance(resolved_target, Mapping):
                node.update(resolved_target)
                node.pop("$ref", None)
                return node
            return resolved_target
        elif isinstance(node, Mapping):
            for k, v in node.items():
                node[k] = _do_resolve(v, resolver, _expanding)
        elif isinstance(node, (list, tuple)):
            for i, _ in enumerate(node):
                node[i] = _do_resolve(node[i], resolver, _expanding)
        return node

    res = _do_resolve(spec, registry.resolver(base_uri))
    return res


def format_error_with_path(exception: ValidationError) -> str:
    """Format a `ValidationError` with path to error."""
    error_path = ".".join(str(item) for item in exception.path)
    error_path_msg = f" - '{error_path}'" if error_path else ""
    return error_path_msg


def allow_nullable(validation_fn: t.Callable) -> t.Callable:
    """Extend an existing validation function, so it allows nullable values to be null."""

    def nullable_validation_fn(validator, to_validate, instance, schema):
        if instance is None and (
            schema.get("x-nullable") is True or schema.get("nullable")
        ):
            return

        yield from validation_fn(validator, to_validate, instance, schema)

    return nullable_validation_fn


def validate_writeOnly(validator, wo, instance, schema):
    yield ValidationError("Property is write-only")


NullableTypeValidator = allow_nullable(Draft4Validator.VALIDATORS["type"])
NullableEnumValidator = allow_nullable(Draft4Validator.VALIDATORS["enum"])

Draft4RequestValidator = extend(
    Draft4Validator,
    {
        "type": NullableTypeValidator,
        "enum": NullableEnumValidator,
    },
)

Draft4ResponseValidator = extend(
    Draft4Validator,
    {
        "type": NullableTypeValidator,
        "enum": NullableEnumValidator,
        "writeOnly": validate_writeOnly,
        "x-writeOnly": validate_writeOnly,
    },
)
