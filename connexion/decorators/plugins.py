import functools
import logging

logger = logging.getLogger('connexion.decorators.plugins')


class BasePlugin(object):
    """Define the standard plugin interface.

    To implement a new plugin, inherit from the base class
    and override the hook functions.
    """

    def __init__(self, api):
        """Initialize the plugin."""
        self.api = api

    def before(self, request):
        """Hook method - called before the request is handled"""
        pass  # pragma: no cover

    def after(self, request, response):
        """Hook method - called after the request is handled"""
        pass  # pragma: no cover


class PluginsDecorator(object):
    """Plugins decorator composed of multiple plugins."""

    def __init__(self, api, plugin_classes):
        """Initialize the plugins decorator.

        :param plugin_classes: list of plugin classes
        :type plugin_classes: list
        """
        self.api = api
        self.plugins = [plugin_class(api=api)
                        for plugin_class in plugin_classes]

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            """Wrap operation with plugins logic."""
            response = None

            logger.debug("%s running plugins 'before' ...", request.url)
            for plugin in self.plugins:
                plugin.before(request)
            try:
                response = function(request)
                return response
            finally:
                logger.debug("%s running plugins 'after' ...", request.url)
                for plugin in self.plugins:
                    plugin.after(request, response)

        return wrapper
