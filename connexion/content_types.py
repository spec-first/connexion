import logging
import re

from jsonschema import ValidationError

from .exceptions import ExtraParameterProblem, BadRequestProblem
from .types import coerce_type
from .utils import is_null

logger = logging.getLogger('connexion.content_types')


class ContentHandler(object):

    def __init__(self, validator, schema, strict, is_null_value_valid):
        self.schema = schema
        self.strict_validation = strict
        self.is_null_value_valid = is_null_value_valid
        self.validator = validator
        self.default = schema.get('default')

    def validate_schema(self, data, url):
        # type: (dict, AnyStr) -> Union[ConnexionResponse, None]
        if is_null(data):
            if self.default:
                # XXX do we need to do this? If the spec is valid, this will pass
                data = self.default
            elif self.is_null_value_valid:
                return

        try:
            self.validator.validate(data)
        except ValidationError as exception:
            error_path = '.'.join(str(item) for item in exception.path)
            error_path_msg = " - '{path}'".format(path=error_path) \
                if error_path else ""
            logger.error(
                "{url} validation error: {error}{error_path_msg}".format(
                    url=url, error=exception.message,
                    error_path_msg=error_path_msg),
                extra={'validator': 'body'})
            raise BadRequestProblem(detail="{message}{error_path_msg}".format(
                               message=exception.message,
                               error_path_msg=error_path_msg))

    def deserialize(self, request):
        return request.body

    def validate(self, request):
        data = self.deserialize(request)
        self.validate_schema(data, request.url)


class StreamingContentHandler(ContentHandler):
    name = "application/octet-stream"
    regex = re.compile(r'^application\/octet-stream.*')

    def validate(self, request):
        # Don't validate, leave stream for user to read
        pass


class JSONContentHandler(ContentHandler):
    name = "application/json"
    regex = re.compile(r'^application\/json.*|^.*\+json$')

    def deserialize(self, request):
        data = request.json
        empty_body = not(request.body or request.form or request.files)
        if data is None and not empty_body and not self.is_null_value_valid:
            # Content-Type is json but actual body was not parsed
            raise BadRequestProblem(detail="Request body is not valid JSON")
        return data


def validate_parameter_list(request_params, spec_params):
    request_params = set(request_params)
    spec_params = set(spec_params)

    return request_params.difference(spec_params)


class FormDataContentHandler(ContentHandler):
    name = "application/x-www-form-urlencoded"
    regex = re.compile(
        r'^application\/x-www-form-urlencoded.*'
    )

    def _validate_formdata_parameter_list(self, request):
        request_params = request.form.keys()
        spec_params = self.schema.get('properties', {}).keys()
        return validate_parameter_list(request_params, spec_params)

    def deserialize(self, request):
        data = dict(request.form.items()) or \
                   (request.body if len(request.body) > 0 else {})
        data.update(dict.fromkeys(request.files, ''))  # validator expects string..
        logger.debug('%s validating schema...', request.url)

        if self.strict_validation:
            formdata_errors = self._validate_formdata_parameter_list(request)
            if formdata_errors:
                raise ExtraParameterProblem(formdata_errors, [])

        if data:
            props = self.schema.get("properties", {})
            for k, param_defn in props.items():
                if k in data:
                    data[k] = coerce_type(param_defn, data[k], 'requestBody', k)
            # XXX it's surprising to hide this in validation
            request.form = data
        return data


class MultiPartFormDataContentHandler(FormDataContentHandler):
    name = "multipart/form-data"
    regex = re.compile(
        r'^multipart\/form-data.*'
    )


KNOWN_CONTENT_TYPES = (
    StreamingContentHandler,
    JSONContentHandler,
    FormDataContentHandler,
    MultiPartFormDataContentHandler
)
