import collections
import copy
import logging

from jsonschema import Draft4Validator, ValidationError
from starlette.requests import Request

from connexion.exceptions import BadRequestProblem, ExtraParameterProblem
from connexion.utils import boolean, is_null, is_nullable

logger = logging.getLogger("connexion.validators.parameter")

TYPE_MAP = {"integer": int, "number": float, "boolean": boolean, "object": dict}

try:
    draft4_format_checker = Draft4Validator.FORMAT_CHECKER  # type: ignore
except AttributeError:  # jsonschema < 4.5.0
    from jsonschema import draft4_format_checker


class ParameterValidator:
    def __init__(
        self,
        parameters,
        uri_parser,
        strict_validation=False,
        security_query_params=None,
    ):
        """
        :param parameters: List of request parameter dictionaries
        :param uri_parser: class to use for uri parsing
        :param strict_validation: Flag indicating if parameters not in spec are allowed
        :param security_query_params: List of query parameter names used for security.
            These parameters will be ignored when checking for extra parameters in case of
            strict validation.
        """
        self.parameters = collections.defaultdict(list)
        for p in parameters:
            self.parameters[p["in"]].append(p)

        self.uri_parser = uri_parser
        self.strict_validation = strict_validation
        self.security_query_params = set(security_query_params or [])

    @staticmethod
    def validate_parameter(parameter_type, value, param, param_name=None):
        if is_nullable(param) and is_null(value):
            return

        elif value is not None:
            param = copy.deepcopy(param)
            param = param.get("schema", param)
            try:
                Draft4Validator(param, format_checker=draft4_format_checker).validate(
                    value
                )
            except ValidationError as exception:
                return str(exception)

        elif param.get("required"):
            return "Missing {parameter_type} parameter '{param[name]}'".format(
                **locals()
            )

    @staticmethod
    def validate_parameter_list(request_params, spec_params):
        request_params = set(request_params)
        spec_params = set(spec_params)

        return request_params.difference(spec_params)

    def validate_query_parameter_list(self, request, security_params=None):
        request_params = request.query_params.keys()
        spec_params = [x["name"] for x in self.parameters.get("query", [])]
        spec_params.extend(security_params or [])
        return self.validate_parameter_list(request_params, spec_params)

    def validate_query_parameter(self, param, request):
        """
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        """
        # Convert to dict of lists
        query_params = {
            k: request.query_params.getlist(k) for k in request.query_params
        }
        query_params = self.uri_parser.resolve_query(query_params)
        val = query_params.get(param["name"])
        return self.validate_parameter("query", val, param)

    def validate_path_parameter(self, param, request):
        path_params = self.uri_parser.resolve_path(request.path_params)
        val = path_params.get(param["name"].replace("-", "_"))
        return self.validate_parameter("path", val, param)

    def validate_header_parameter(self, param, request):
        val = request.headers.get(param["name"])
        return self.validate_parameter("header", val, param)

    def validate_cookie_parameter(self, param, request):
        val = request.cookies.get(param["name"])
        return self.validate_parameter("cookie", val, param)

    def validate(self, scope):
        logger.debug("%s validating parameters...", scope.get("path"))

        request = Request(scope)
        self.validate_request(request)

    def validate_request(self, request):
        if self.strict_validation:
            query_errors = self.validate_query_parameter_list(
                request, security_params=self.security_query_params
            )

            if query_errors:
                raise ExtraParameterProblem(
                    param_type="query", extra_params=query_errors
                )

        for param in self.parameters.get("query", []):
            error = self.validate_query_parameter(param, request)
            if error:
                raise BadRequestProblem(detail=error)

        for param in self.parameters.get("path", []):
            error = self.validate_path_parameter(param, request)
            if error:
                raise BadRequestProblem(detail=error)

        for param in self.parameters.get("header", []):
            error = self.validate_header_parameter(param, request)
            if error:
                raise BadRequestProblem(detail=error)

        for param in self.parameters.get("cookie", []):
            error = self.validate_cookie_parameter(param, request)
            if error:
                raise BadRequestProblem(detail=error)
