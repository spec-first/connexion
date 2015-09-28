"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

# Decorators to change the return type of endpoints
import datetime
import flask
import functools
import json
import logging

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


class BaseSerializer:
    def __init__(self, mimetype='text/plain'):
        """
        :type mimetype: str
        """
        self.mimetype = mimetype

    @staticmethod
    def get_data_status_code(data):
        """
        :type data: flask.Response | (object, int) | object
        :rtype: (object, int)
        """
        url = flask.request.url
        logger.debug('Getting data and status code', extra={'data': data, 'data_type': type(data), 'url': url})
        if isinstance(data, flask.Response):
            data = data
            status_code = data.status_code
        elif isinstance(data, tuple) and len(data) == 2:
            data, status_code = data
        else:
            status_code = 200
        logger.debug('Got data and status code (%d)', status_code, extra={'data': data,
                                                                          'data_type': type(data),
                                                                          'url': url})
        return data, status_code

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        return function

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
            data, status_code = self.get_data_status_code(function(*args, **kwargs))
            logger.debug('Returning %s', url, extra={'url': url, 'mimetype': self.mimetype})
            if isinstance(data, flask.Response):  # if the function returns a Response object don't change it
                logger.debug('Endpoint returned a Flask Response', extra={'url': url, 'mimetype': data.mimetype})
                return data

            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
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
            data, status_code = self.get_data_status_code(function(*args, **kwargs))
            if isinstance(data, flask.Response):  # if the function returns a Response object don't change it
                logger.debug('Endpoint returned a Flask Response', extra={'url': url, 'mimetype': data.mimetype})
                return data
            elif data is NoContent:
                return '', status_code
            elif status_code == 204:
                logger.debug('Endpoint returned an empty response (204)', extra={'url': url, 'mimetype': self.mimetype})
                return '', 204

            data = json.dumps(data, indent=2, cls=JSONEncoder)
            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            return response, status_code

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return '<Jsonifier: {}>'.format(self.mimetype)
