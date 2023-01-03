"""
This module defines an AbstractAPI, which defines a standardized interface for a Connexion API.
"""
import abc
import logging
import pathlib
import sys
import typing as t

from connexion.exceptions import ResolverError
from connexion.http_facts import METHODS
from connexion.jsonifier import Jsonifier
from connexion.lifecycle import ConnexionRequest, MiddlewareRequest
from connexion.operations import make_operation
from connexion.options import ConnexionOptions
from connexion.resolver import Resolver
from connexion.spec import Specification

MODULE_PATH = pathlib.Path(__file__).absolute().parent.parent
SWAGGER_UI_URL = "ui"

logger = logging.getLogger("connexion.apis.abstract")


class AbstractAPIMeta(abc.ABCMeta):
    def __init__(cls, name, bases, attrs):
        abc.ABCMeta.__init__(cls, name, bases, attrs)
        cls._set_jsonifier()


class AbstractSpecAPI(metaclass=AbstractAPIMeta):
    def __init__(
        self,
        specification: t.Union[pathlib.Path, str, dict],
        base_path: t.Optional[str] = None,
        resolver: t.Optional[Resolver] = None,
        arguments: t.Optional[dict] = None,
        options: t.Optional[dict] = None,
        *args,
        **kwargs,
    ):
        """Base API class with only minimal behavior related to the specification.

        :param specification: OpenAPI specification. Can be provided either as dict, or as path
            to file.
        :param base_path: Base path to host the API.
        :param resolver: Callable that maps operationID to a function
        :param resolver_error_handler: Callable that generates an Operation used for handling
            ResolveErrors
        :param arguments: Jinja arguments to resolve in specification.
        :param options: New style options dictionary.
        """
        logger.debug(
            "Loading specification: %s",
            specification,
            extra={
                "swagger_yaml": specification,
                "base_path": base_path,
                "arguments": arguments,
            },
        )

        # Avoid validator having ability to modify specification
        self.specification = Specification.load(specification, arguments=arguments)

        logger.debug("Read specification", extra={"spec": self.specification})

        self.options = ConnexionOptions(options, oas_version=self.specification.version)

        logger.debug(
            "Options Loaded",
            extra={
                "swagger_ui": self.options.openapi_console_ui_available,
                "swagger_path": self.options.openapi_console_ui_from_dir,
                "swagger_url": self.options.openapi_console_ui_path,
            },
        )

        self._set_base_path(base_path)

        self.resolver = resolver or Resolver()

    def _set_base_path(self, base_path: t.Optional[str] = None) -> None:
        if base_path is not None:
            # update spec to include user-provided base_path
            self.specification.base_path = base_path
            self.base_path = base_path
        else:
            self.base_path = self.specification.base_path

    @classmethod
    def _set_jsonifier(cls):
        cls.jsonifier = Jsonifier()


class AbstractRoutingAPI(AbstractSpecAPI):
    def __init__(
        self,
        *args,
        resolver_error_handler: t.Optional[t.Callable] = None,
        pythonic_params=False,
        **kwargs,
    ) -> None:
        """Minimal interface of an API, with only functionality related to routing.

        :param pythonic_params: When True CamelCase parameters are converted to snake_case and an underscore is appended
            to any shadowed built-ins
        """
        super().__init__(*args, **kwargs)
        logger.debug("Pythonic params: %s", str(pythonic_params))
        self.pythonic_params = pythonic_params
        self.resolver_error_handler = resolver_error_handler

        self.add_paths()

    def add_paths(self, paths: t.Optional[dict] = None) -> None:
        """
        Adds the paths defined in the specification as endpoints
        """
        paths = paths or self.specification.get("paths", dict())
        for path, methods in paths.items():
            logger.debug("Adding %s%s...", self.base_path, path)

            for method in methods:
                if method not in METHODS:
                    continue
                try:
                    self.add_operation(path, method)
                except ResolverError as err:
                    # If we have an error handler for resolver errors, add it as an operation.
                    # Otherwise treat it as any other error.
                    if self.resolver_error_handler is not None:
                        self._add_resolver_error_handler(method, path, err)
                    else:
                        self._handle_add_operation_error(path, method, err.exc_info)
                except Exception:
                    # All other relevant exceptions should be handled as well.
                    self._handle_add_operation_error(path, method, sys.exc_info())

    def add_operation(self, path: str, method: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _add_operation_internal(self, method: str, path: str, operation: t.Any) -> None:
        """
        Adds the operation according to the user framework in use.
        It will be used to register the operation on the user framework router.
        """

    def _add_resolver_error_handler(self, method: str, path: str, err: ResolverError):
        """
        Adds a handler for ResolverError for the given method and path.
        """
        self.resolver_error_handler = t.cast(t.Callable, self.resolver_error_handler)
        operation = self.resolver_error_handler(
            err,
        )
        self._add_operation_internal(method, path, operation)

    def _handle_add_operation_error(self, path: str, method: str, exc_info: tuple):
        url = f"{self.base_path}{path}"
        error_msg = "Failed to add operation for {method} {url}".format(
            method=method.upper(), url=url
        )
        logger.error(error_msg)
        _type, value, traceback = exc_info
        raise value.with_traceback(traceback)


class AbstractAPI(AbstractRoutingAPI, metaclass=AbstractAPIMeta):
    """
    Defines an abstract interface for a Swagger API
    """

    def __init__(
        self,
        specification,
        base_path=None,
        arguments=None,
        resolver=None,
        resolver_error_handler=None,
        options=None,
        **kwargs,
    ):
        """
        :type resolver_error_handler: callable | None
        :type pythonic_params: bool
        """

        super().__init__(
            specification,
            base_path=base_path,
            arguments=arguments,
            resolver=resolver,
            resolver_error_handler=resolver_error_handler,
            options=options,
            **kwargs,
        )

    def add_operation(self, path, method):
        """
        Adds one operation to the api.

        This method uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.

        :type method: str
        :type path: str
        """
        operation = make_operation(
            self.specification,
            self,
            path,
            method,
            self.resolver,
            uri_parser_class=self.options.uri_parser_class,
        )
        self._add_operation_internal(method, path, operation)

    @staticmethod
    @abc.abstractmethod
    def get_request(
        **kwargs,
    ) -> t.Union[ConnexionRequest, MiddlewareRequest]:
        """
        This method converts the user framework request to a ConnexionRequest.
        """

    @classmethod
    @abc.abstractmethod
    def is_framework_response(cls, response):
        """Return True if `response` is a framework response class"""

    @classmethod
    @abc.abstractmethod
    def connexion_to_framework_response(cls, response):
        """Cast ConnexionResponse to framework response class"""

    @classmethod
    @abc.abstractmethod
    def build_response(
        cls,
        data,
        content_type=None,
        status_code=None,
        headers=None,
    ):
        """
        Create a framework response from the provided arguments.
        :param data: Body data.
        :param content_type: The response status code.
        :type content_type: str
        :type status_code: int
        :param headers: The response status code.
        :type headers: Union[Iterable[Tuple[str, str]], Dict[str, str]]
        :return A framework response.
        :rtype Response
        """

    def json_loads(self, data):
        return self.jsonifier.loads(data)
