import pathlib
from typing import Optional  # NOQA

MODULE_PATH = pathlib.Path(__file__).absolute().parent
INTERNAL_CONSOLE_UI_PATH = MODULE_PATH / 'vendor' / 'swagger-ui'


class ConnexionOptions(object):
    def __init__(self, options=None):
        self._options = {}
        if options:
            self._options.update(filter_values(options))

    def extend(self, new_values=None):
        # type: (Optional[dict]) -> ConnexionOptions
        """
        Return a new instance of `ConnexionOptions` using as default the currently
        defined options.
        """
        if new_values is None:
            new_values = {}

        options = dict(self._options)
        options.update(filter_values(new_values))
        return ConnexionOptions(options)

    def as_dict(self):
        return self._options

    @property
    def openapi_spec_available(self):
        # type: () -> bool
        """
        Whether to make available the OpenAPI Specification under
        `openapi_console_ui_path`/swagger.json path.

        Default: True
        """
        # NOTE: Under OpenAPI v3 this should change to "/openapi.json"
        return self._options.get('swagger_json', True)

    @property
    def openapi_console_ui_available(self):
        # type: () -> bool
        """
        Whether to make the OpenAPI Console UI available under the path
        defined in `openapi_console_ui_path` option. Note that if enabled,
        this overrides the `openapi_spec_available` option since the specification
        is required to be available via a HTTP endpoint to display the console UI.

        Default: True
        """
        return self._options.get('swagger_ui', True)

    @property
    def openapi_console_ui_path(self):
        # type: () -> str
        """
        Path to mount the OpenAPI Console UI and make it accessible via a browser.

        Default: /ui
        """
        return self._options.get('swagger_url', '/ui')

    @property
    def openapi_console_ui_from_dir(self):
        # type: () -> str
        """
        Custom OpenAPI Console UI directory from where Connexion will serve
        the static files.

        Default: Connexion's vendored version of the OpenAPI Console UI.
        """
        return self._options.get('swagger_path', INTERNAL_CONSOLE_UI_PATH)


def filter_values(dictionary):
    # type: (dict) -> dict
    """
    Remove `None` value entries in the dictionary.

    :param dictionary:
    :return:
    """
    return dict([(key, value)
                 for key, value in dictionary.items()
                 if value is not None])
