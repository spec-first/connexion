# Decorators to change the return type of endpoints
import datetime
import functools
import logging

import flask
from flask import json

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

        return json.JSONEncoder.default(self, o)


class BaseSerializer(BaseDecorator):
    def __init__(self, mimetype='text/plain'):
        """
        :type mimetype: str
        """
        self.mimetype = mimetype

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
            response = function(*args, **kwargs)
            logger.debug('Returning %s', url,
                         extra={'url': url, 'mimetype': self.mimetype})
            return response

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Produces: {}>'.format(self.mimetype)


class Jsonifier(BaseSerializer):
    @staticmethod
    def dumps(data):
        """ Central point where JSON serialization happens inside
        Connexion.
        """
        return "{}\n".format(json.dumps(data, indent=2))

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            url = flask.request.url

            logger.debug('Jsonifing %s', url,
                         extra={'url': url, 'mimetype': self.mimetype})

            response = function(*args, **kwargs)

            if response.is_handler_response_object:
                logger.debug('Endpoint returned a Flask Response',
                             extra={'url': url, 'mimetype': self.mimetype})
                return response

            elif response.data is NoContent:
                response.set_data('')
                return response

            elif response.status_code == 204:
                logger.debug('Endpoint returned an empty response (204)',
                             extra={'url': url, 'mimetype': self.mimetype})
                response.set_data('')
                return response

            elif response.mimetype == 'application/problem+json' and isinstance(response.data, str):
                # connexion.problem() already adds data as a serialized JSON
                return response

            json_content = Jsonifier.dumps(response.get_data())
            response.set_data(json_content)
            return response

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Jsonifier: {}>'.format(self.mimetype)
