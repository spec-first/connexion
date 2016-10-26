# Decorators to change the return type of endpoints
import datetime
import functools
import logging

import flask
from flask import json

from ..utils import is_flask_response
from .decorator import BaseDecorator

logger = logging.getLogger('connexion.decorators.produces')

# special marker object to return empty content for any status code
# e.g. in app method do "return NoContent, 201"
NoContent = object()


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            if o.tzinfo:
                # eg: '2015-09-25T23:14:42.588601+00:00'
                return o.isoformat('T')
            else:
                # No timezone present - assume UTC.
                # eg: '2015-09-25T23:14:42.588601Z'
                return o.isoformat('T') + 'Z'

        if isinstance(o, datetime.date):
            return o.isoformat()
        
        if isinstance(o, datetime.timedelta):
            return (datetime.datetime.min + o).time().isoformat()

        return json.JSONEncoder.default(self, o)


class BaseSerializer(BaseDecorator):
    def __init__(self, mimetype='text/plain'):
        """
        :type mimetype: str
        """
        self.mimetype = mimetype

    @staticmethod
    def process_headers(response, headers):
        """
        A convenience function for updating the Response headers with any additional headers
        generated in the view. If more complex logic should be needed later then it can be handled here.

        :type response: flask.Response
        :type headers: dict
        :rtype flask.Response
        """
        if headers:
            response.headers.extend(headers)
        return response

    def __repr__(self):
        """
        :rtype: str
        """
        return '<BaseSerializer: {}>'.format(self.mimetype)


class Produces(BaseSerializer):
    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            url = flask.request.url
            data, status_code, headers = self.get_full_response(function(*args, **kwargs))
            logger.debug('Returning %s', url, extra={'url': url, 'mimetype': self.mimetype})
            if is_flask_response(data):
                logger.debug('Endpoint returned a Flask Response', extra={'url': url, 'mimetype': data.mimetype})
                return data

            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            response = self.process_headers(response, headers)

            return response, status_code

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Produces: {}>'.format(self.mimetype)


class Jsonifier(BaseSerializer):
    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            url = flask.request.url
            logger.debug('Jsonifing %s', url, extra={'url': url, 'mimetype': self.mimetype})
            data, status_code, headers = self.get_full_response(function(*args, **kwargs))
            if is_flask_response(data):
                logger.debug('Endpoint returned a Flask Response', extra={'url': url, 'mimetype': data.mimetype})
                return data
            elif data is NoContent:
                return '', status_code, headers
            elif status_code == 204:
                logger.debug('Endpoint returned an empty response (204)', extra={'url': url, 'mimetype': self.mimetype})
                return '', 204, headers

            data = [json.dumps(data, indent=2), '\n']
            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            response = self.process_headers(response, headers)

            return response, status_code

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Jsonifier: {}>'.format(self.mimetype)
