import pathlib
import json
from jsonschema.compat import urlsplit

import yaml
import jinja2
from swagger_spec_validator.validator20 import validate_spec as _validate_spec


def file_resolver(url, base_path, jinja2_env=None, arguments=None):
    arguments = arguments or {}
    if base_path is None:
        split = urlsplit(url)
        path = pathlib.Path(split.path)
    else:
        path = base_path / url.lstrip('/')
    is_yaml = any(path.suffix.startswith(ext) for ext in ('.yaml', '.yml'))
    is_jinja2 = any(path.suffix.endswith(ext) for ext in ('.j2',))

    if is_jinja2 and jinja2_env is not None:
        swagger_string = jinja2_env.get_template(str(path.name)).render(**arguments)
        return yaml.safe_load(swagger_string) if is_yaml else json.loads(swagger_string)
    elif is_jinja2 and jinja2_env is None:
        with path.open(mode='rb') as resolved_file:
            contents = resolved_file.read()
            try:
                swagger_template = contents.decode()
            except UnicodeDecodeError:
                swagger_template = contents.decode('utf-8', 'replace')

            swagger_string = jinja2.Template(swagger_template).render(**arguments)
        return yaml.safe_load(swagger_string) if is_yaml else json.loads(swagger_string)
    else:
        with path.open(mode='rb') as resolved_file:
            return yaml.safe_load(resolved_file) if is_yaml else json.load(resolved_file)


def get_reference_resolvers(base_path, jinja2_env=None, arguments=None):
    base_path = str(base_path) if base_path is not None else None
    return {
        '': lambda url: file_resolver(url=url, base_path=base_path, jinja2_env=jinja2_env, arguments=arguments),
        'file': lambda url: file_resolver(url=url, base_path=None),
    }


def load_spec_string_from_file(arguments, specification, jinja2_env=None):
    arguments = arguments or {}

    if jinja2_env is None:
        with specification.open(mode='rb') as swagger_yaml:
            contents = swagger_yaml.read()
            try:
                swagger_template = contents.decode()
            except UnicodeDecodeError:
                swagger_template = contents.decode('utf-8', 'replace')

            return jinja2.Template(swagger_template).render(**arguments)
    else:
        return jinja2_env.get_template(str(specification.name)).render(**arguments)


def load_spec_from_file(arguments, specification, jinja2_env=None):
    swagger_string = load_spec_string_from_file(arguments, specification, jinja2_env)
    return yaml.safe_load(swagger_string)  # type: dict


def validate_spec(spec, specification_dir=None, jinja2_env=None, arguments=None):
    return _validate_spec(spec, http_handlers=get_reference_resolvers(specification_dir, jinja2_env, arguments))


def compatibility_layer(spec):
    """Make specs compatible with older versions of Connexion."""
    if not isinstance(spec, dict):
        return spec

    # Make all response codes be string
    for path_name, methods_available in spec.get('paths', {}).items():
        for method_name, method_def in methods_available.items():
            if (method_name == 'parameters' or not isinstance(
                    method_def, dict)):
                continue

            response_definitions = {}
            for response_code, response_def in method_def.get(
                    'responses', {}).items():
                response_definitions[str(response_code)] = response_def

            method_def['responses'] = response_definitions
    return spec
