#!/usr/bin/env python3
import flask
from flask import jsonify, redirect

import connexion
from connexion import NoContent, ProblemException, problem


class DummyClass(object):
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
    data = {'greeting': 'Hello {name}'.format(name=name)}
    return data

def post_greeting3(body, **kwargs):
    print(body)
    data = {'greeting': 'Hello {name}'.format(name=body["name"])}
    return data

def post_greeting_url(name, remainder, **kwargs):
    data = {'greeting': 'Hello {name} thanks for {remainder}'.format(name=name,remainder=remainder)}
    return data

def post_goodday(name):
    data = {'greeting': 'Hello {name}'.format(name=name)}
    headers = {"Location": "/my/uri"}
    return data, 201, headers


def post_goodday_no_header():
    return {'greeting': 'Hello.'}, 201


def post_goodevening(name):
    data = 'Good evening {name}'.format(name=name)
    headers = {"Location": "/my/uri"}
    return data, 201, headers


def get_list(name):
    data = ['hello', name]
    return data


def get_bye(name):
    return 'Goodbye {name}'.format(name=name)


def get_flask_response_tuple():
    return jsonify({'foo': 'bar'}), 201


def get_bye_secure(name, user, token_info):
    return 'Goodbye {name} (Secure: {user})'.format(name=name, user=user)


def get_bye_secure_from_flask():
    return 'Goodbye {user} (Secure!)'.format(user=flask.request.user)


def get_bye_secure_from_connexion():
    return 'Goodbye {user} (Secure!)'.format(user=connexion.request.user)


def get_bye_secure_ignoring_context(name):
    return 'Goodbye {name} (Secure!)'.format(name=name)


def with_problem():
    return problem(type='http://www.example.com/error',
                   title='Some Error',
                   detail='Something went wrong somewhere',
                   status=418,
                   instance='instance1',
                   headers={'x-Test-Header': 'In Test'})


def with_problem_txt():
    return problem(title='Some Error',
                   detail='Something went wrong somewhere',
                   status=418,
                   instance='instance1')


def internal_error():
    return 42 / 0


def get_greetings(name):
    """
    Used to test custom mimetypes
    """
    data = {'greetings': 'Hello {name}'.format(name=name)}
    return data


def multimime():
    return 'Goodbye'


def empty():
    return None, 204


def schema(new_stack):
    return new_stack


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


def test_array_csv_query_param(items):
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


def test_default_integer_body(stack_version):
    return stack_version


def test_falsy_param(falsy):
    return falsy


def test_formdata_param(body):
    return body["formData"]


def test_formdata_missing_param():
    return ''


def test_formdata_file_upload(formData):
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
    return problem(403, "You need to pay", "Missing amount",
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


def test_args_kwargs(*args, **kwargs):
    return kwargs


def test_param_sanitization(query=None, form=None):
    result = {}
    if query:
        result['query'] = query
    if form:
        result['form'] = form
    return result


def test_body_sanitization(body=None):
    return body


def post_wrong_content_type():
    return "NOT OK"


def get_unicode_query(price=None):
    return {'price': price}


def get_unicode_data():
    jsonResponse = {u'currency': u'\xa3', u'key': u'leena'}
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
