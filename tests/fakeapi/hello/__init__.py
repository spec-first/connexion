#!/usr/bin/env python3
import datetime
import uuid

from connexion import NoContent, ProblemException, context, request
from flask import jsonify, redirect


class DummyClass:
    @classmethod
    def test_classmethod(cls):
        return cls.__name__

    def test_method(self):
        return self.__class__.__name__

class_instance = DummyClass()  # noqa


def get():
    return ''


def search():
    return ''


def api_list():
    return 'a'


def post():
    return ''


def post_greeting(name, **kwargs):
    data = {'greeting': f'Hello {name}'}
    return data

def post_greeting3(body, **kwargs):
    data = {'greeting': 'Hello {name}'.format(name=body["name"])}
    return data

def post_greeting_url(name, remainder, **kwargs):
    data = {'greeting': f'Hello {name} thanks for {remainder}'}
    return data

def post_goodday(name):
    data = {'greeting': f'Hello {name}'}
    headers = {"Location": "/my/uri"}
    return data, 201, headers


def post_goodday_no_header():
    return {'greeting': 'Hello.'}, 201


def post_goodevening(name):
    data = f'Good evening {name}'
    headers = {"Location": "/my/uri"}
    return data, 201, headers


def get_list(name):
    data = ['hello', name]
    return data


def get_bye(name):
    return f'Goodbye {name}'


def get_flask_response_tuple():
    return jsonify({'foo': 'bar'}), 201


def get_bye_secure(name, user, token_info):
    return f'Goodbye {name} (Secure: {user})'


def get_bye_secure_from_flask():
    return 'Goodbye {user} (Secure!)'.format(user=context['user'])


def get_bye_secure_from_connexion(req_context):
    return 'Goodbye {user} (Secure!)'.format(user=req_context['user'])


def get_bye_secure_ignoring_context(name):
    return f'Goodbye {name} (Secure!)'

def get_bye_secure_jwt(name, user, token_info):
    return f'Goodbye {name} (Secure: {user})'

def with_problem():
    raise ProblemException(type='http://www.example.com/error',
                           title='Some Error',
                           detail='Something went wrong somewhere',
                           status=418,
                           instance='instance1',
                           headers={'x-Test-Header': 'In Test'})


def with_problem_txt():
    raise ProblemException(title='Some Error',
                           detail='Something went wrong somewhere',
                           status=418,
                           instance='instance1')


def internal_error():
    return 42 / 0


def get_greetings(name):
    """
    Used to test custom mimetypes
    """
    data = {'greetings': f'Hello {name}'}
    return data


def multimime():
    return 'Goodbye'


def empty():
    return None, 204


def schema(new_stack):
    return new_stack


def forward(body):
    """Return a response with the same payload as in the request body."""
    return body


def schema_response_object(valid):
    if valid == "invalid_requirements":
        return {"docker_version": 1.0}
    elif valid == "invalid_type":
        return {"image_version": 1.0}
    else:
        return {"image_version": "1.0"}  # valid


def schema_response_string(valid):
    if valid == "valid":
        return "Image version 2.0"
    else:
        return 2.0


def schema_response_integer(valid):
    if valid == "valid":
        return 3
    else:
        return 3.0


def schema_response_number(valid):
    if valid == "valid":
        return 4.0
    else:
        return "Four"


def schema_response_boolean(valid):
    if valid == "valid":
        return True
    else:
        return "yes"


def schema_response_array(valid):
    if valid == "invalid_dict":
        return {
            {"image_version": "1.0"}:
                {"image_version": "2.0"}
        }
    elif valid == "invalid_string":
        return "Not an array."
    else:
        return [
            {"image_version": "1.0"},
            {"image_version": "2.0"}
        ]


def schema_query(image_version=None):
    return {'image_version': image_version}


def schema_list():
    return ''


def schema_map():
    return ''


def schema_recursive():
    return ''


def schema_format():
    return ''


def test_parameter_validation():
    return ''


def test_required_query_param():
    return ''


def test_apikey_query_parameter_validation():
    return ''


def test_array_csv_query_param(items):
    return items


def test_array_pipes_form_param3(items):
    return items['items']


def test_array_csv_form_param3(items):
    return items['items']


def test_array_pipes_form_param(items):
    return items


def test_array_csv_form_param(items):
    return items


def test_array_multi_query_param(items):
    return items


def test_array_pipes_query_param(items):
    return items


def test_array_unsupported_query_param(items):
    return items


def test_no_content_response():
    return NoContent, 204


def test_schema_array(test_array):
    return test_array


def test_schema_int(test_int):
    return test_int


def test_get_someint(someint):
    return type(someint).__name__


def test_get_somefloat(somefloat):
    return type(somefloat).__name__


def test_default_param(name):
    return {"app_name": name}


def test_default_object_body(stack):
    return {"stack": stack}

def test_nested_additional_properties(body):
    return body

def test_default_integer_body(stack_version):
    return stack_version


def test_empty_object_body(stack):
    return {"stack": stack}


def test_falsy_param(falsy):
    return falsy

def test_formdata_param3(body):
    return body["formData"]


def test_formdata_param(formData):
    return formData


def test_formdata_missing_param():
    return ''


def test_formdata_file_upload(formData, **kwargs):
    filename = formData.filename
    contents = formData.read().decode('utf-8', 'replace')
    return {filename: contents}


def test_formdata_file_upload_missing_param():
    return ''


def test_bool_default_param(thruthiness):
    return thruthiness


def test_bool_array_param(thruthiness=None):
    if thruthiness is None:
        thruthiness = []
    return all(thruthiness)


def test_required_param(simple):
    return simple


def test_exploded_deep_object_param(id):
    return id


def test_nested_exploded_deep_object_param(id):
    return id


def test_exploded_deep_object_param_additional_properties(id):
    return id


def test_redirect_endpoint():
    headers = {'Location': 'http://www.google.com/'}
    return '', 302, headers


def test_redirect_response_endpoint():
    return redirect('http://www.google.com/')


def test_204_with_headers():
    headers = {'X-Something': 'test'}
    return '', 204, headers


def test_nocontent_obj_with_headers():
    headers = {'X-Something': 'test'}
    return NoContent, 204, headers


def path_parameters_in_get_method(title):
    return [title], 200, {}


def test_default_missmatch_definition(age):
    return 'OK'


def test_array_in_path(names):
    return names, 200


def test_global_response_definition():
    return ['general', 'list'], 200


def test_nullable_parameters(time_start):
    if time_start is None:
        return 'it was None'
    return time_start


def test_nullable_param_post(post_param):
    if post_param is None:
        return 'it was None'
    return post_param


def test_nullable_param_post3(body):
    if body is None:
        return 'it was None'
    if body["post_param"] is None:
        return 'it was None'
    return body["post_param"]


def test_nullable_param_put(contents):
    if contents is None:
        return 'it was None'
    return contents


def test_custom_json_response():
    return {'theResult': DummyClass()}, 200


def get_blob_data():
    return b'cool\x00\x08'


def get_data_as_binary():
    return get_blob_data(), 200, {'Content-Type': 'application/octet-stream'}


def get_data_as_text(post_param):
    return ''


def get_invalid_response():
    return {"simple": object()}


def get_empty_dict():
    return {}


def get_custom_problem_response():
    raise ProblemException(403, "You need to pay", "Missing amount",
                           ext={'amount': 23.0})


def throw_problem_exception():
    raise ProblemException(
        title="As Exception",
        detail="Something wrong or not!",
        ext={'age': 30}
    )


def unordered_params_response(first, path_param, second):
    return dict(first=int(first), path_param=str(path_param), second=int(second))


def more_than_one_scope_defined(**kwargs):
    return "OK"


def optional_auth(**kwargs):
    key = apikey_info(request.headers.get('X-AUTH'))
    if key is None:
        return "Unauthenticated"
    else:
        return "Authenticated"


def test_args_kwargs(*args, **kwargs):
    return kwargs


def test_param_sanitization(query=None, form=None):
    result = {}
    if query:
        result['query'] = query
    if form:
        result['form'] = form
    return result


def test_param_sanitization3(query=None, body=None):
    result = {}
    if query:
        result['query'] = query
    if body:
        result['form'] = body["form"]
    return result


def test_body_sanitization(body=None):
    return body

def test_body_sanitization_additional_properties(body):
    return body

def test_body_sanitization_additional_properties_defined(body):
    return body

def test_body_not_allowed_additional_properties(body):
    return body

def post_wrong_content_type():
    return "NOT OK"


def get_unicode_query(price=None):
    return {'price': price}


def get_unicode_data():
    jsonResponse = {'currency': '\xa3', 'key': 'leena'}
    return jsonResponse


def get_enum_response():
    try:
        from enum import Enum
        class HTTPStatus(Enum):
            OK = 200
    except ImportError:
        return {}, 200
    else:
        return {}, HTTPStatus.OK


def get_httpstatus_response():
    try:
        from http import HTTPStatus
    except ImportError:
        return {}, 200
    else:
        return {}, HTTPStatus.OK


def get_bad_default_response(response_code):
    return {}, response_code


def get_user():
    return {'user_id': 7, 'name': 'max'}


def get_user_with_password():
    return {'user_id': 7, 'name': 'max', 'password': '5678'}


def post_user(body):
    body['user_id'] = 8
    body.pop('password', None)
    return body

def post_multipart_form(body):
    x = body['x']
    x['name'] += "-reply"
    x['age'] += 10
    return x


def apikey_info(apikey, required_scopes=None):
    if apikey == 'mykey':
        return {'sub': 'admin'}
    return None


def jwt_info(token):
    if token == '100':
        return {'sub': '100'}
    return None


def get_add_operation_on_http_methods_only():
    return ""


def put_add_operation_on_http_methods_only():
    return ""


def post_add_operation_on_http_methods_only():
    return ""


def delete_add_operation_on_http_methods_only():
    return ""


def options_add_operation_on_http_methods_only():
    return ""


def head_add_operation_on_http_methods_only():
    return ""


def patch_add_operation_on_http_methods_only():
    return ""


def trace_add_operation_on_http_methods_only():
    return ""


def get_datetime():
    return {'value': datetime.datetime(2000, 1, 2, 3, 4, 5, 6)}


def get_date():
    return {'value': datetime.date(2000, 1, 2)}


def get_uuid():
    return {'value': uuid.UUID(hex='e7ff66d0-3ec2-4c4e-bed0-6e4723c24c51')}
