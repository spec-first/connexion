"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""
import logging

import flask

from ..utils import is_flask_response

logger = logging.getLogger('connexion.decorators.decorator')


class BaseDecorator(object):

    @staticmethod
    def get_full_response(data):
        """
        Gets Data. Status Code and Headers for response.
        If only body data is returned by the endpoint function, then the status code will be set to 200 and no headers
        will be added.
        If the returned object is a flask.Response then it will just pass the information needed to recreate it.

        :type data: flask.Response | (object, int) | (object, int, dict) | object
        :rtype: (object, int, dict)
        """
        url = flask.request.url
        logger.debug('Getting data and status code', extra={'data': data, 'data_type': type(data), 'url': url})
        status_code, headers = 200, {}
        if is_flask_response(data):
            data = data
            status_code = data.status_code
            headers = data.headers
        elif isinstance(data, tuple) and len(data) == 3:
            data, status_code, headers = data
        elif isinstance(data, tuple) and len(data) == 2:
            data, status_code = data
        logger.debug('Got data and status code (%d)', status_code, extra={'data': data,
                                                                          'data_type': type(data),
                                                                          'url': url})
        return data, status_code, headers

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
        return '<BaseDecorator: {}>'
