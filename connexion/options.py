"""
This module defines a Connexion specific options class to pass to the Connexion App or API.
"""
import dataclasses
import logging
import typing as t

try:
    from swagger_ui_bundle import swagger_ui_path as default_template_dir
except ImportError:
    default_template_dir = None

NO_UI_MSG = """The swagger_ui directory could not be found.
    Please install connexion with extra install: pip install connexion[swagger-ui]
    or provide the path to your local installation by passing swagger_path=<your path>
"""

logger = logging.getLogger("connexion.options")


@dataclasses.dataclass
class SwaggerUIOptions:
    """Options to configure the Swagger UI.

    :param serve_spec: Whether to serve the Swagger / OpenAPI Specification
    :param spec_path: Where to serve the Swagger / OpenAPI Specification

    :param swagger_ui: Whether to serve the Swagger UI
    :param swagger_ui_path: Where to serve the Swagger UI
    :param swagger_ui_config: Options to configure the Swagger UI. See
          https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration
          for an overview of the available options.
    :param swagger_ui_template_dir: Directory with static files to use to serve Swagger UI
    :param swagger_ui_template_arguments: Arguments passed to the Swagger UI template. Useful
        when providing your own template dir with additional template arguments.
    """

    serve_spec: bool = True
    spec_path: t.Optional[str] = None

    swagger_ui: bool = True
    swagger_ui_config: dict = dataclasses.field(default_factory=dict)
    swagger_ui_path: str = "/ui"
    swagger_ui_template_dir: t.Optional[str] = None
    swagger_ui_template_arguments: dict = dataclasses.field(default_factory=dict)


class SwaggerUIConfig:
    """Class holding swagger UI specific options."""

    def __init__(
        self,
        options: t.Optional[SwaggerUIOptions] = None,
        oas_version: t.Tuple[int, ...] = (2,),
    ):
        if oas_version >= (3, 0, 0):
            self.spec_path = "/openapi.json"
        else:
            self.spec_path = "/swagger.json"

        if options is not None and not isinstance(options, SwaggerUIOptions):
            raise ValueError(
                f"`swaggger_ui_options` should be of type `SwaggerUIOptions`, "
                f"but received {type(options)} instead."
            )

        self._options = options or SwaggerUIOptions()

    @property
    def openapi_spec_available(self) -> bool:
        """Whether to make the OpenAPI Specification available."""
        return self._options.serve_spec

    @property
    def openapi_spec_path(self) -> str:
        """Path to host the Swagger UI."""
        return self._options.spec_path or self.spec_path

    @property
    def swagger_ui_available(self) -> bool:
        """Whether to make the Swagger UI available."""
        if self._options.swagger_ui and self.swagger_ui_template_dir is None:
            logger.warning(NO_UI_MSG)
            return False
        return self._options.swagger_ui

    @property
    def swagger_ui_path(self) -> str:
        """Path to mount the Swagger UI and make it accessible via a browser."""
        return self._options.swagger_ui_path

    @property
    def swagger_ui_template_dir(self) -> str:
        """Directory with static files to use to serve Swagger UI."""
        return self._options.swagger_ui_template_dir or default_template_dir

    @property
    def swagger_ui_config(self) -> dict:
        """Options to configure the Swagger UI."""
        return self._options.swagger_ui_config

    @property
    def swagger_ui_template_arguments(self) -> dict:
        """Arguments passed to the Swagger UI template."""
        return self._options.swagger_ui_template_arguments
