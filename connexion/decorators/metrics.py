
import functools
import os

try:
    import uwsgi_metrics
    HAS_UWSGI_METRICS = True
except:
    HAS_UWSGI_METRICS = False


class UWSGIMetricsCollector:
    def __init__(self, path, method):
        self.path = path
        self.method = method
        self.key = '{}.{}'.format(self.path.strip('/').replace('/', '.').replace('<', '{').replace('>', '}'),
                                  self.method.upper())
        self.prefix = os.getenv('HTTP_METRICS_PREFIX', 'connexion.response')

    @staticmethod
    def is_available():
        return HAS_UWSGI_METRICS

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            with uwsgi_metrics.timing(self.prefix, self.key):
                return function(*args, **kwargs)

        return wrapper
