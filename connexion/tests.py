import abc
import functools

import six


class AbstractClientMeta(abc.ABCMeta):
    pass


@six.add_metaclass(AbstractClientMeta)
class AbstractClient(object):
    """A test client to run tests on top of different web frameworks."""
    http_verbs = [
        "head",
        "get",
        "delete",
        "options",
        "patch",
        "post",
        "put",
        "trace",
    ]

    def __init__(self, app):
        self.app = app

    @classmethod
    def from_app(cls, app):
        return cls(app)

    @abc.abstractmethod
    def _request(
        self,
        method,
        url,
        headers=None,
        data=None,
        json=None,
        content_type=None,
    ):
        # type: (...) -> connexion.lifecycle.ConnexionResponse
        """Make request and return a ConnexionResponse instance.

        For now, the expected client has to be compatible with flask's test_client.
        TODO: use the arguments from ConnexionRequest if one day Apis have a method
        to translate ConnexionRequest to web framework request.
        see https://github.com/pallets/werkzeug/blob/master/werkzeug/test.py#L222
        for the request client.
        """

    def __getattr__(self, key):
        """Call _request with method bound if key is an HTTP method."""
        if key in self.http_verbs:
            return functools.partial(self._request, key)
        raise AttributeError(key)
