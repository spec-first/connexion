import logging
import re
import xmltodict

from jsonschema import ValidationError

from .exceptions import ExtraParameterProblem, BadRequestProblem
from .types import coerce_type
from .utils import is_null

logger = logging.getLogger(__name__)


class ContentHandlerFactory(object):

    def __init__(self, validator, schema, strict_validation,
                 is_null_value_valid, consumes):
        self.validator = validator
        self.schema = schema
        self.strict_validation = strict_validation
        self.is_null_value_valid = is_null_value_valid
        self.consumes = consumes
        self._content_handlers = self._discover()

    def _discover(self):
        content_handlers = ContentHandler.discover_subclasses()
        return {
            name: cls(self.validator, self.schema,
                      self.strict_validation, self.is_null_value_valid)
            for name, cls in content_handlers.items()
        }

    def get_handler(self, content_type):
        match = None

        if content_type is None:
            return match

        media_type = content_type.split(";", 1)[0]
        if media_type not in self.consumes:
            return None

        try:
            return self._content_handlers[media_type]
        except KeyError:
            pass

        matches = [
            (name, handler) for name, handler in self._content_handlers.items()
            if handler.regex.match(content_type)
        ]
        if len(matches) > 1:
            logger.warning(f"Content could be handled by multiple validators: {matches}")

        if matches:
            name, handler = matches[0]
            return handler


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
                # TODO do we need to do this? If the spec is valid, this will pass
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

    def validate_request(self, request):
        data = self.deserialize(request)
        self.validate_schema(data, request.url)

    @classmethod
    def discover_subclasses(cls):
        subclasses = {c.name: c for c in cls.__subclasses__()}
        for s in cls.__subclasses__():
            subclasses.update(s.discover_subclasses())
        return subclasses


class XMLContentHandler(ContentHandler):
    name = "application/xml"
    regex = re.compile(r'^application\/xml.*')

    def validate_request(self, request):
        # Don't validate, leave stream for user to read
        xml_content = request.body
        data = xmltodict.parse(xml_content)
        request.xml = data
        return data


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
