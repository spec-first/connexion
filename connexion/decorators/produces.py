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
import flask
import functools
import json
import types


class Produces:
    def __init__(self, mimetype='application/json'):
        self.mimetype = mimetype

    def __call__(self, function: types.FunctionType):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = function(*args, **kwargs)
            if isinstance(data, tuple) and len(data) == 2:
                data, status_code = data
            else:
                status_code = 200
            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            return response, status_code
        return wrapper


class Jsonifier(Produces):

    def __call__(self, function: types.FunctionType):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            data = function(*args, **kwargs)

            if isinstance(data, tuple) and len(data) == 2:
                data, status_code = data
            else:
                status_code = 200
            data = json.dumps(data, indent=2)
            response = flask.current_app.response_class(data, mimetype=self.mimetype)  # type: flask.Response
            return response, status_code
        return wrapper
