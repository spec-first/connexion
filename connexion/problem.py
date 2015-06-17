"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""
import flask
import json


def problem(type='about:blank', *, title: str, detail: str, status: int, instance: str=None):
    problem_response = {'type': type, 'title': title, 'detail': detail, 'status': status, }
    if instance:
        problem_response['instance'] = instance

    return flask.current_app.response_class(json.dumps(problem_response),
                                            mimetype='application/problem+json',
                                            status=status)
