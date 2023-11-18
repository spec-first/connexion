import json
from io import BytesIO
from typing import List

import pytest


def test_parameter_validation(simple_app):
    app_client = simple_app.test_client()

    url = "/v1.0/test_parameter_validation"

    response = app_client.get(url, params={"date": "2015-08-26"})
    assert response.status_code == 200

    for invalid_int in "", "foo", "0.1":
        response = app_client.get(url, params={"int": invalid_int})
        assert response.status_code == 400

    response = app_client.get(url, params={"int": "123"})
    assert response.status_code == 200

    for invalid_bool in "", "foo", "yes":
        response = app_client.get(url, params={"bool": invalid_bool})
        assert response.status_code == 400

    response = app_client.get(url, params={"bool": "true"})
    assert response.status_code == 200


def test_required_query_param(simple_app):
    app_client = simple_app.test_client()

    url = "/v1.0/test_required_query_param"
    response = app_client.get(url)
    assert response.status_code == 400

    response = app_client.get(url, params={"n": "1.23"})
    assert response.status_code == 200


def test_array_query_param(simple_app):
    app_client = simple_app.test_client()
    headers = {"Content-type": "application/json"}
    url = "/v1.0/test_array_csv_query_param"
    response = app_client.get(url, headers=headers)
    array_response: List[str] = response.json()
    assert array_response == ["squash", "banana"]
    url = "/v1.0/test_array_csv_query_param?items=one,two,three"
    response = app_client.get(url, headers=headers)
    array_response: List[str] = response.json()
    assert array_response == ["one", "two", "three"]
    url = "/v1.0/test_array_pipes_query_param?items=1|2|3"
    response = app_client.get(url, headers=headers)
    array_response: List[int] = response.json()
    assert array_response == [1, 2, 3]
    url = "/v1.0/test_array_unsupported_query_param?items=1;2;3"
    response = app_client.get(url, headers=headers)
    array_response: List[str] = response.json()  # unsupported collectionFormat
    assert array_response == ["1;2;3"]
    url = "/v1.0/test_array_csv_query_param?items=A&items=B&items=C&items=D,E,F"
    response = app_client.get(url, headers=headers)
    array_response: List[str] = response.json()  # multi array with csv format
    assert array_response == ["D", "E", "F"]
    url = "/v1.0/test_array_multi_query_param?items=A&items=B&items=C&items=D,E,F"
    response = app_client.get(url, headers=headers)
    array_response: List[str] = response.json()  # multi array with csv format
    assert array_response == ["A", "B", "C", "D", "E", "F"]
    url = "/v1.0/test_array_pipes_query_param?items=4&items=5&items=6&items=7|8|9"
    response = app_client.get(url, headers=headers)
    array_response: List[int] = response.json()  # multi array with pipes format
    assert array_response == [7, 8, 9]


def test_array_form_param(simple_app):
    app_client = simple_app.test_client()
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    url = "/v1.0/test_array_csv_form_param"
    response = app_client.post(url, headers=headers)
    array_response: List[str] = response.json()
    assert array_response == ["squash", "banana"]
    url = "/v1.0/test_array_csv_form_param"
    response = app_client.post(url, headers=headers, data={"items": "one,two,three"})
    array_response: List[str] = response.json()
    assert array_response == ["one", "two", "three"]
    url = "/v1.0/test_array_pipes_form_param"
    response = app_client.post(url, headers=headers, data={"items": "1|2|3"})
    array_response: List[int] = response.json()
    assert array_response == [1, 2, 3]
    url = "/v1.0/test_array_csv_form_param"
    data = "items=A&items=B&items=C&items=D,E,F"
    response = app_client.post(url, headers=headers, content=data)
    array_response: List[str] = response.json()  # multi array with csv format
    assert array_response == ["D", "E", "F"]
    url = "/v1.0/test_array_pipes_form_param"
    data = "items=4&items=5&items=6&items=7|8|9"
    response = app_client.post(url, headers=headers, content=data)
    array_response: List[int] = response.json()  # multi array with pipes format
    assert array_response == [7, 8, 9]


def test_extra_query_param(simple_app):
    app_client = simple_app.test_client()
    headers = {"Content-type": "application/json"}
    url = "/v1.0/test_parameter_validation?extra_parameter=true"
    resp = app_client.get(url, headers=headers)
    assert resp.status_code == 200


def test_strict_extra_query_param(strict_app):
    app_client = strict_app.test_client()
    headers = {"Content-type": "application/json"}
    url = "/v1.0/test_parameter_validation?extra_parameter=true"
    resp = app_client.get(url, headers=headers)
    assert resp.status_code == 400
    response = resp.json()
    assert response["detail"] == "Extra query parameter(s) extra_parameter not in spec"


def test_strict_formdata_param(strict_app):
    app_client = strict_app.test_client()
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    url = "/v1.0/test_array_csv_form_param"
    resp = app_client.post(url, headers=headers, data={"items": "mango"})
    response = resp.json()
    assert response == ["mango"]
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "arg, result",
    [
        # The cases accepted by the Flask/Werkzeug converter
        ["123", "int 123"],
        ["0", "int 0"],
        ["0000", "int 0"],
        # Additional cases that we want to support
        ["+123", "int 123"],
        ["+0", "int 0"],
        ["-0", "int 0"],
        ["-123", "int -123"],
    ],
)
def test_path_parameter_someint(simple_app, arg, result):
    assert isinstance(arg, str)  # sanity check
    app_client = simple_app.test_client()
    resp = app_client.get(f"/v1.0/test-int-path/{arg}")
    assert resp.text == f'"{result}"\n'


def test_path_parameter_someint__bad(simple_app):
    # non-integer values will not match Flask route
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-int-path/foo")
    assert resp.status_code == 404, resp.text


@pytest.mark.parametrize(
    "arg, result",
    [
        # The cases accepted by the Flask/Werkzeug converter
        ["123.45", "float 123.45"],
        ["123.0", "float 123"],
        ["0.999999999999999999", "float 1"],
        # Additional cases that we want to support
        ["+123.45", "float 123.45"],
        ["-123.45", "float -123.45"],
        ["123.", "float 123"],
        [".45", "float 0.45"],
        ["123", "float 123"],
        ["0", "float 0"],
        ["0000", "float 0"],
        ["-0.000000001", "float -1e-09"],
        ["100000000000", "float 1e+11"],
    ],
)
def test_path_parameter_somefloat(simple_app, arg, result):
    assert isinstance(arg, str)  # sanity check
    app_client = simple_app.test_client()
    resp = app_client.get(f"/v1.0/test-float-path/{arg}")
    assert resp.text == f'"{result}"\n'


@pytest.mark.parametrize(
    "arg, arg2, result",
    [
        ["-0.000000001", "0.3", "float -1e-09, 0.3"],
    ],
)
def test_path_parameter_doublefloat(simple_app, arg, arg2, result):
    assert isinstance(arg, str) and isinstance(arg2, str)  # sanity check
    app_client = simple_app.test_client()
    resp = app_client.get(f"/v1.0/test-float-path/{arg}/{arg2}")
    assert resp.text == f'"{result}"\n'


def test_path_parameter_somefloat__bad(simple_app):
    # non-float values will not match Flask route
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-float-path/123,45")
    assert resp.status_code == 404, resp.text


def test_default_param(strict_app):
    app_client = strict_app.test_client()
    resp = app_client.get("/v1.0/test-default-query-parameter")
    assert resp.status_code == 200
    response = resp.json()
    assert response["app_name"] == "connexion"


def test_falsy_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-falsy-param", params={"falsy": 0})
    assert resp.status_code == 200
    response = resp.json()
    assert response == 0

    resp = app_client.get("/v1.0/test-falsy-param")
    assert resp.status_code == 200
    response = resp.json()
    assert response == 1


def test_formdata_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post("/v1.0/test-formData-param", data={"formData": "test"})
    assert resp.status_code == 200
    response = resp.json()
    assert response == "test"


def test_formdata_bad_request(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post("/v1.0/test-formData-param")
    assert resp.status_code == 400
    response = resp.json()
    assert response["detail"] in [
        "Missing formdata parameter 'formData'",
        "'formData' is a required property",  # OAS3
    ]


def test_formdata_missing_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-formData-missing-param", data={"missing_formData": "test"}
    )
    assert resp.status_code == 200


def test_formdata_extra_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-formData-param", data={"formData": "test", "extra_formData": "test"}
    )
    assert resp.status_code == 200


def test_strict_formdata_extra_param(strict_app):
    app_client = strict_app.test_client()
    resp = app_client.post(
        "/v1.0/test-formData-param", data={"formData": "test", "extra_formData": "test"}
    )
    assert resp.status_code == 400
    assert (
        resp.json()["detail"]
        == "Extra formData parameter(s) extra_formData not in spec"
    )


def test_formdata_file_upload(simple_app):
    """Test that a single file is accepted and provided to the user as a file object if the openapi
    specification defines single file. Do not accept multiple files."""
    app_client = simple_app.test_client()

    resp = app_client.post(
        "/v1.0/test-formData-file-upload",
        files=[
            ("file", ("filename.txt", BytesIO(b"file contents"))),
            ("file", ("filename2.txt", BytesIO(b"file2 contents"))),
        ],
    )
    assert resp.status_code == 400

    resp = app_client.post(
        "/v1.0/test-formData-file-upload",
        files={"file": ("filename.txt", BytesIO(b"file contents"))},
    )
    assert resp.status_code == 200
    assert resp.json() == {"filename.txt": "file contents"}


def test_formdata_multiple_file_upload(simple_app):
    """Test that multiple files are accepted and provided to the user as a list if the openapi
    specification defines an array of files."""
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-formData-multiple-file-upload",
        files=[
            ("file", ("filename.txt", BytesIO(b"file contents"))),
            ("file", ("filename2.txt", BytesIO(b"file2 contents"))),
        ],
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "filename.txt": "file contents",
        "filename2.txt": "file2 contents",
    }

    resp = app_client.post(
        "/v1.0/test-formData-multiple-file-upload",
        files={"file": ("filename.txt", BytesIO(b"file contents"))},
    )
    assert resp.status_code == 200
    assert resp.json() == {"filename.txt": "file contents"}


def test_mixed_formdata(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-mixed-formData",
        data={"formData": "test"},
        files={"file": ("filename.txt", BytesIO(b"file contents"))},
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "data": {"formData": "test"},
        "files": {
            "filename.txt": "file contents",
        },
    }


def test_formdata_file_upload_bad_request(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-formData-file-upload",
        headers={"Content-Type": b"multipart/form-data; boundary=-"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] in [
        "Missing formdata parameter 'file'",
        "'file' is a required property",  # OAS3
    ]


def test_formdata_file_upload_missing_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post(
        "/v1.0/test-formData-file-upload-missing-param",
        files={"missing_fileData": ("example.txt", BytesIO(b"file contents"))},
    )
    assert resp.status_code == 200, resp.text


def test_body_not_allowed_additional_properties(simple_app):
    app_client = simple_app.test_client()
    body = {"body1": "bodyString", "additional_property": "test1"}
    resp = app_client.post(
        "/v1.0/body-not-allowed-additional-properties",
        json=body,
    )
    assert resp.status_code == 400

    response = resp.json()
    assert "Additional properties are not allowed" in response["detail"]


def test_body_in_get_request(simple_app):
    app_client = simple_app.test_client()
    body = {"body1": "bodyString"}
    resp = app_client.request(
        "GET",
        "/v1.0/body-in-get-request",
        json=body,
    )
    assert resp.status_code == 200
    assert resp.json() == body


def test_bool_as_default_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-bool-param")
    assert resp.status_code == 200

    resp = app_client.get("/v1.0/test-bool-param", params={"thruthiness": True})
    assert resp.status_code == 200
    response = resp.json()
    assert response is True


def test_bool_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-bool-param", params={"thruthiness": True})
    assert resp.status_code == 200
    response = resp.json()
    assert response is True

    resp = app_client.get("/v1.0/test-bool-param", params={"thruthiness": False})
    assert resp.status_code == 200
    response = resp.json()
    assert response is False


def test_bool_array_param(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-bool-array-param?thruthiness=true,true,true")
    assert resp.status_code == 200, resp.text
    response = resp.json()
    assert response is True

    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-bool-array-param?thruthiness=true,true,false")
    assert resp.status_code == 200, resp.text
    response = resp.json()
    assert response is False

    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-bool-array-param")
    assert resp.status_code == 200, resp.text


def test_required_param_miss_config(simple_app):
    app_client = simple_app.test_client()

    resp = app_client.get("/v1.0/test-required-param")
    assert resp.status_code == 400

    resp = app_client.get("/v1.0/test-required-param", params={"simple": "test"})
    assert resp.status_code == 200

    resp = app_client.get("/v1.0/test-required-param")
    assert resp.status_code == 400


def test_parameters_defined_in_path_level(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/parameters-in-root-path?title=nice-get")
    assert resp.status_code == 200
    assert resp.json() == ["nice-get"]

    resp = app_client.get("/v1.0/parameters-in-root-path")
    assert resp.status_code == 400


def test_array_in_path(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/test-array-in-path/one_item")
    assert resp.json() == ["one_item"]

    resp = app_client.get("/v1.0/test-array-in-path/one_item,another_item")
    assert resp.json() == [
        "one_item",
        "another_item",
    ]


def test_nullable_parameter(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/nullable-parameters?time_start=null")
    assert resp.json() == "it was None"

    resp = app_client.get("/v1.0/nullable-parameters?time_start=None")
    assert resp.json() == "it was None"

    time_start = 1010
    resp = app_client.get(f"/v1.0/nullable-parameters?time_start={time_start}")
    assert resp.json() == time_start

    resp = app_client.post("/v1.0/nullable-parameters", data={"post_param": "None"})
    assert resp.json() == "it was None"

    resp = app_client.post("/v1.0/nullable-parameters", data={"post_param": "null"})
    assert resp.json() == "it was None"

    headers = {"Content-Type": "application/json"}
    resp = app_client.put("/v1.0/nullable-parameters", content="null", headers=headers)
    assert resp.json() == "it was None"

    resp = app_client.put(
        "/v1.0/nullable-parameters-noargs", content="null", headers=headers
    )
    assert resp.json() == "hello"


def test_args_kwargs(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/query-params-as-kwargs")
    assert resp.status_code == 200
    assert resp.json() == {}

    resp = app_client.get("/v1.0/query-params-as-kwargs?foo=a&bar=b")
    assert resp.status_code == 200
    assert resp.json() == {"foo": "a"}

    if simple_app._spec_file == "openapi.yaml":
        body = {"foo": "a", "bar": "b"}
        resp = app_client.post(
            "/v1.0/body-params-as-kwargs",
            json=body,
        )
        assert resp.status_code == 200
        # having only kwargs, the handler would have been passed 'body'
        assert resp.json() == {
            "body": {"foo": "a", "bar": "b"},
        }


def test_param_sanitization(simple_app):
    app_client = simple_app.test_client()
    resp = app_client.post("/v1.0/param-sanitization")
    assert resp.status_code == 200
    assert resp.json() == {}

    resp = app_client.post(
        "/v1.0/param-sanitization?$query=queryString", data={"$form": "formString"}
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "query": "queryString",
        "form": "formString",
    }

    body = {"body1": "bodyString", "body2": "otherString"}
    resp = app_client.post(
        "/v1.0/body-sanitization",
        json=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json() == body

    body = {"body1": "bodyString", "body2": 12, "body3": {"a": "otherString"}}
    resp = app_client.post(
        "/v1.0/body-sanitization-additional-properties",
        json=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json() == body

    body = {
        "body1": "bodyString",
        "additional_property": "test1",
        "additional_property2": "test2",
    }
    resp = app_client.post(
        "/v1.0/body-sanitization-additional-properties-defined",
        json=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json() == body


def test_no_sanitization_in_request_body(simple_app):
    app_client = simple_app.test_client()
    data = {
        "name": "John",
        "$surname": "Doe",
        "1337": True,
        "!#/bin/sh": False,
        "(1/0)": "division by zero",
        "s/$/EOL/": "regular expression",
        "@8am": "time",
    }
    response = app_client.post("/v1.0/forward", json=data)

    assert response.status_code == 200
    assert response.json() == data


def test_parameters_snake_case(snake_case_app):
    app_client = snake_case_app.test_client()
    headers = {"Content-type": "application/json"}
    resp = app_client.post(
        "/v1.0/test-post-path-snake/123",
        headers=headers,
        json={"a": "test"},
    )
    assert resp.status_code == 200
    resp = app_client.post(
        "/v1.0/test-post-path-shadow/123",
        headers=headers,
        json={"a": "test"},
    )
    assert resp.status_code == 200
    resp = app_client.post(
        "/v1.0/test-post-query-snake?someId=123",
        headers=headers,
        json={"a": "test"},
    )
    assert resp.status_code == 200
    resp = app_client.post(
        "/v1.0/test-post-query-shadow?id=123&class=header",
        headers=headers,
        json={"a": "test"},
    )
    assert resp.status_code == 200
    resp = app_client.get("/v1.0/test-get-path-snake/123")
    assert resp.status_code == 200
    resp = app_client.get("/v1.0/test-get-path-shadow/123")
    assert resp.status_code == 200
    resp = app_client.get("/v1.0/test-get-query-snake?someId=123")
    assert resp.status_code == 200
    resp = app_client.get("/v1.0/test-get-query-shadow?list=123")
    assert resp.status_code == 200
    # Tests for when CamelCase parameter is supplied, of which the snake_case version
    # matches an existing parameter and view func argument, or vice versa
    resp = app_client.get(
        "/v1.0/test-get-camel-case-version?truthiness=true&orderBy=asc"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"truthiness": True, "order_by": "asc"}
    resp = app_client.get("/v1.0/test-get-camel-case-version?truthiness=5")
    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("'5' is not of type 'boolean'")
    # Incorrectly cased params should be ignored
    resp = app_client.get(
        "/v1.0/test-get-camel-case-version?Truthiness=true&order_by=asc"
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "truthiness": False,
        "order_by": None,
    }  # default values
    resp = app_client.get("/v1.0/test-get-camel-case-version?Truthiness=5&order_by=4")
    assert resp.status_code == 200
    assert resp.json() == {
        "truthiness": False,
        "order_by": None,
    }  # default values
    # TODO: Add tests for body parameters


def test_get_unicode_request(simple_app):
    """Regression test for Python 2 UnicodeEncodeError bug during parameter parsing."""
    app_client = simple_app.test_client()
    resp = app_client.get("/v1.0/get_unicode_request?price=%C2%A319.99")  # £19.99
    assert resp.status_code == 200
    assert resp.json()["price"] == "£19.99"


def test_cookie_param(simple_app):
    app_client = simple_app.test_client(cookies={"test_cookie": "hello"})
    response = app_client.get("/v1.0/test-cookie-param")
    assert response.status_code == 200
    assert response.json() == {"cookie_value": "hello"}
