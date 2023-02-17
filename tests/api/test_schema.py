import json


def test_schema(schema_app):
    app_client = schema_app.test_client()

    empty_request = app_client.post("/v1.0/test_schema", json={})
    assert empty_request.status_code == 400
    assert empty_request.headers.get("content-type") == "application/problem+json"
    empty_request_response = empty_request.json()
    assert empty_request_response["title"] == "Bad Request"
    assert empty_request_response["detail"].startswith(
        "'image_version' is a required property"
    )

    bad_type = app_client.post("/v1.0/test_schema", json={"image_version": 22})
    assert bad_type.status_code == 400
    assert bad_type.headers.get("content-type") == "application/problem+json"
    bad_type_response = bad_type.json()
    assert bad_type_response["title"] == "Bad Request"
    assert bad_type_response["detail"].startswith("22 is not of type 'string'")

    bad_type_path = app_client.post("/v1.0/test_schema", json={"image_version": 22})
    assert bad_type_path.status_code == 400
    assert bad_type_path.headers.get("content-type") == "application/problem+json"
    bad_type_path_response = bad_type_path.json()
    assert bad_type_path_response["title"] == "Bad Request"
    assert bad_type_path_response["detail"].endswith(" - 'image_version'")

    good_request = app_client.post(
        "/v1.0/test_schema",
        json={"image_version": "version"},
    )
    assert good_request.status_code == 200
    good_request_response = good_request.json()
    assert good_request_response["image_version"] == "version"

    good_request_extra = app_client.post(
        "/v1.0/test_schema",
        json={"image_version": "version", "extra": "stuff"},
    )
    assert good_request_extra.status_code == 200
    good_request_extra_response = good_request.json()
    assert good_request_extra_response["image_version"] == "version"

    wrong_type = app_client.post("/v1.0/test_schema", json=42)
    assert wrong_type.status_code == 400
    assert wrong_type.headers.get("content-type") == "application/problem+json"
    wrong_type_response = wrong_type.json()
    assert wrong_type_response["title"] == "Bad Request"
    assert wrong_type_response["detail"].startswith("42 is not of type 'object'")


def test_schema_response(schema_app):
    app_client = schema_app.test_client()

    request = app_client.get(
        "/v1.0/test_schema/response/object/valid",
    )
    assert request.status_code == 200, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/object/invalid_type",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/object/invalid_requirements",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/string/valid",
    )
    assert request.status_code == 200, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/string/invalid",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/integer/valid",
    )
    assert request.status_code == 200, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/integer/invalid",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/number/valid",
    )
    assert request.status_code == 200, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/number/invalid",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/boolean/valid",
    )
    assert request.status_code == 200, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/boolean/invalid",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/array/valid",
    )
    assert request.status_code == 200, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/array/invalid_dict",
    )
    assert request.status_code == 500, request.text
    request = app_client.get(
        "/v1.0/test_schema/response/array/invalid_string",
    )
    assert request.status_code == 500, request.text


def test_schema_in_query(schema_app):
    app_client = schema_app.test_client()
    headers = {"Content-type": "application/json"}

    good_request = app_client.post(
        "/v1.0/test_schema_in_query",
        headers=headers,
        params={"image_version": "version", "not_required": "test"},
    )
    assert good_request.status_code == 200
    good_request_response = good_request.json()
    assert good_request_response["image_version"] == "version"


def test_schema_list(schema_app):
    app_client = schema_app.test_client()

    wrong_type = app_client.post("/v1.0/test_schema_list", json=42)
    assert wrong_type.status_code == 400
    assert wrong_type.headers.get("content-type") == "application/problem+json"
    wrong_type_response = wrong_type.json()
    assert wrong_type_response["title"] == "Bad Request"
    assert wrong_type_response["detail"].startswith("42 is not of type 'array'")

    wrong_items = app_client.post("/v1.0/test_schema_list", json=[42])
    assert wrong_items.status_code == 400
    assert wrong_items.headers.get("content-type") == "application/problem+json"
    wrong_items_response = wrong_items.json()
    assert wrong_items_response["title"] == "Bad Request"
    assert wrong_items_response["detail"].startswith("42 is not of type 'string'")


def test_schema_map(schema_app):
    app_client = schema_app.test_client()

    valid_object = {
        "foo": {"image_version": "string"},
        "bar": {"image_version": "string"},
    }

    invalid_object = {"foo": 42}

    wrong_type = app_client.post("/v1.0/test_schema_map", json=42)
    assert wrong_type.status_code == 400
    assert wrong_type.headers.get("content-type") == "application/problem+json"
    wrong_type_response = wrong_type.json()
    assert wrong_type_response["title"] == "Bad Request"
    assert wrong_type_response["detail"].startswith("42 is not of type 'object'")

    wrong_items = app_client.post("/v1.0/test_schema_map", json=invalid_object)
    assert wrong_items.status_code == 400
    assert wrong_items.headers.get("content-type") == "application/problem+json"
    wrong_items_response = wrong_items.json()
    assert wrong_items_response["title"] == "Bad Request"
    assert wrong_items_response["detail"].startswith("42 is not of type 'object'")

    right_type = app_client.post("/v1.0/test_schema_map", json=valid_object)
    assert right_type.status_code == 200


def test_schema_recursive(schema_app):
    app_client = schema_app.test_client()

    valid_object = {
        "children": [
            {"children": []},
            {
                "children": [
                    {"children": []},
                ]
            },
            {"children": []},
        ]
    }

    invalid_object = {"children": [42]}

    wrong_type = app_client.post("/v1.0/test_schema_recursive", json=42)
    assert wrong_type.status_code == 400
    assert wrong_type.headers.get("content-type") == "application/problem+json"
    wrong_type_response = wrong_type.json()
    assert wrong_type_response["title"] == "Bad Request"
    assert wrong_type_response["detail"].startswith("42 is not of type 'object'")

    wrong_items = app_client.post("/v1.0/test_schema_recursive", json=invalid_object)
    assert wrong_items.status_code == 400
    assert wrong_items.headers.get("content-type") == "application/problem+json"
    wrong_items_response = wrong_items.json()
    assert wrong_items_response["title"] == "Bad Request"
    assert wrong_items_response["detail"].startswith("42 is not of type 'object'")

    right_type = app_client.post("/v1.0/test_schema_recursive", json=valid_object)
    assert right_type.status_code == 200


def test_schema_format(schema_app):
    app_client = schema_app.test_client()

    wrong_type = app_client.post("/v1.0/test_schema_format", json="xy")
    assert wrong_type.status_code == 400
    assert wrong_type.headers.get("content-type") == "application/problem+json"
    wrong_type_response = wrong_type.json()
    assert wrong_type_response["title"] == "Bad Request"
    assert "'xy' is not a 'email'" in wrong_type_response["detail"]


def test_schema_array(schema_app):
    app_client = schema_app.test_client()

    array_request = app_client.post("/v1.0/schema_array", json=["list", "hello"])
    assert array_request.status_code == 200
    assert array_request.headers.get("content-type") == "application/json"
    array_response = array_request.json()
    assert array_response == ["list", "hello"]


def test_schema_int(schema_app):
    app_client = schema_app.test_client()
    headers = {"Content-type": "application/json"}

    array_request = app_client.post("/v1.0/schema_int", json=42)
    assert array_request.status_code == 200
    assert array_request.headers.get("content-type") == "application/json"
    array_response = array_request.json()  # type: list
    assert array_response == 42


def test_global_response_definitions(schema_app):
    app_client = schema_app.test_client()
    resp = app_client.get("/v1.0/define_global_response")
    assert resp.json() == ["general", "list"]


def test_media_range(schema_app):
    app_client = schema_app.test_client()

    array_request = app_client.post("/v1.0/media_range", json={})
    assert array_request.status_code == 200, array_request.text
