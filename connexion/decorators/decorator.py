import functools
import logging

import flask

from ..utils import is_flask_response

logger = logging.getLogger('connexion.decorators.decorator')


class BaseDecorator(object):

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        return function

    def __repr__(self):  # pragma: no cover
        """
        :rtype: str
        """
        return '<BaseDecorator>'


class BeginOfRequestLifecycleDecorator(BaseDecorator):
    """Manages the lifecycle of the request internally in Connexion.

    Transforms the operation handler response into a `ResponseContainer`
    that can be manipulated by the series of decorators during the
    lifecycle of the request.
    """

    def __init__(self, mimetype):
        self.mimetype = mimetype

    def get_response_container(self, operation_handler_result):
        """Gets ResponseContainer instance for the operation handler
        result. Status Code and Headers for response.  If only body
        data is returned by the endpoint function, then the status
        code will be set to 200 and no headers will be added.

        If the returned object is a flask.Response then it will just
        pass the information needed to recreate it.

        :type operation_handler_result: flask.Response | (flask.Response, int) | (flask.Response, int, dict)
        :rtype: ResponseContainer
        """
        url = flask.request.url
        logger.debug('Getting data and status code',
                     extra={
                         'data': operation_handler_result,
                         'data_type': type(operation_handler_result),
                         'url': url
                     })

        response_container = None
        if is_flask_response(operation_handler_result):
            response_container = ResponseContainer(
                self.mimetype, response=operation_handler_result)

        elif isinstance(operation_handler_result, ResponseContainer):
            response_container = operation_handler_result

        elif isinstance(operation_handler_result, tuple) and len(
                operation_handler_result) == 3:
            data, status_code, headers = operation_handler_result
            response_container = ResponseContainer(
                self.mimetype, data=data, status_code=status_code, headers=headers)

        elif isinstance(operation_handler_result, tuple) and len(
                operation_handler_result) == 2:
            data, status_code = operation_handler_result
            response_container = ResponseContainer(
                self.mimetype, data=data, status_code=status_code)
        else:
            response_container = ResponseContainer(
                self.mimetype, data=operation_handler_result)

        logger.debug('Got data and status code (%d)',
                     response_container.status_code,
                     extra={
                         'data': operation_handler_result,
                         'datatype': type(operation_handler_result),
                         'url': url
                     })

        return response_container

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            operation_handler_result = function(*args, **kwargs)
            return self.get_response_container(operation_handler_result)

        return wrapper


class EndOfRequestLifecycleDecorator(BaseDecorator):
    """Manages the lifecycle of the request internally in Connexion.

    Filter the ResponseContainer instance to return the corresponding
    flask.Response object.
    """

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            response_container = function(*args, **kwargs)
            return response_container.flask_response_object()

        return wrapper


class ResponseContainer(object):
    """ Internal response object to be passed among Connexion
    decorators that want to manipulate response data.

    Partially matches the flask.Response interface for easy access and
    manipulation.

    The methods ResponseContainer#get_data and ResponseContainer#set_data
    are added here following the recommendation found in:

    http://flask.pocoo.org/docs/0.11/api/#flask.Response.data
    """

    def __init__(self, mimetype, data=None, status_code=200, headers=None, response=None):
        """
        :type data: dict | None
        :type status_code: int | None
        :type headers: dict | None
        :type response: flask.Response | None
        """
        self.mimetype = mimetype
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}

        self._response = response
        self.is_handler_response_object = bool(response)

        if self._response:
            self.data = self._response.get_data()
            self.status_code = self._response.status_code
            self.headers = self._response.headers

    def get_data(self):
        """ Get the current data to be used when creating the
        flask.Response instance.
        """
        return self.data

    def set_data(self, data):
        """ Gets the data that is going to be used to create the
        flask.Response instance.
        """
        self.data = data

    def flask_response_object(self):
        """
        Builds an Flask response using the contained data,
        status_code, and headers.

        :rtype: flask.Response
        """
        self._response = flask.current_app.response_class(
            self.data, mimetype=self.mimetype, content_type=self.headers.get('content-type'),
            headers=self.headers)  # type: flask.Response
        self._response.status_code = self.status_code

        return self._response
