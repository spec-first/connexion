import math
from unittest.mock import MagicMock

import connexion.apps
import pytest
from connexion import utils


def test_get_function_from_name():
    function = utils.get_function_from_name("math.ceil")
    assert function == math.ceil
    assert function(2.7) == 3


def test_get_function_from_name_no_module():
    with pytest.raises(ValueError):
        utils.get_function_from_name("math")


def test_get_function_from_name_attr_error(monkeypatch):
    """
    Test attribute error without import error on get_function_from_name.
    Attribute errors due to import errors are tested on
    test_api.test_invalid_operation_does_stop_application_to_setup
    """
    deep_attr_mock = MagicMock()
    deep_attr_mock.side_effect = AttributeError
    monkeypatch.setattr("connexion.utils.deep_getattr", deep_attr_mock)
    with pytest.raises(AttributeError):
        utils.get_function_from_name("math.ceil")


def test_get_function_from_name_for_class_method():
    function = utils.get_function_from_name("connexion.FlaskApp.add_error_handler")
    assert function == connexion.FlaskApp.add_error_handler


def test_boolean():
    assert utils.boolean("true")
    assert utils.boolean("True")
    assert utils.boolean("TRUE")
    assert utils.boolean(True)
    assert not utils.boolean("false")
    assert not utils.boolean("False")
    assert not utils.boolean("FALSE")
    assert not utils.boolean(False)

    with pytest.raises(ValueError):
        utils.boolean("foo")

    with pytest.raises(ValueError):
        utils.boolean(None)


def test_deep_get_dict():
    obj = {"type": "object", "properties": {"id": {"type": "string"}}}
    assert utils.deep_get(obj, ["properties", "id"]) == {"type": "string"}


def test_deep_get_list():
    obj = [{"type": "object", "properties": {"id": {"type": "string"}}}]
    assert utils.deep_get(obj, ["0", "properties", "id"]) == {"type": "string"}


def test_is_json_mimetype():
    assert utils.is_json_mimetype("application/json")
    assert utils.is_json_mimetype("application/vnd.com.myEntreprise.v6+json")
    assert utils.is_json_mimetype(
        "application/vnd.scanner.adapter.vuln.report.harbor+json; version=1.0"
    )
    assert utils.is_json_mimetype(
        "application/vnd.com.myEntreprise.v6+json; charset=UTF-8"
    )
    assert not utils.is_json_mimetype("text/html")


def test_sort_routes():
    routes = ["/users/me", "/users/{username}"]
    expected = ["/users/me", "/users/{username}"]
    assert utils.sort_routes(routes) == expected

    routes = ["/{path:path}", "/basepath/{path:path}"]
    expected = ["/basepath/{path:path}", "/{path:path}"]
    assert utils.sort_routes(routes) == expected

    routes = ["/", "/basepath"]
    expected = ["/basepath", "/"]
    assert utils.sort_routes(routes) == expected

    routes = ["/basepath/{path:path}", "/basepath/v2/{path:path}"]
    expected = ["/basepath/v2/{path:path}", "/basepath/{path:path}"]
    assert utils.sort_routes(routes) == expected

    routes = ["/basepath", "/basepath/v2"]
    expected = ["/basepath/v2", "/basepath"]
    assert utils.sort_routes(routes) == expected

    routes = ["/users/{username}", "/users/me"]
    expected = ["/users/me", "/users/{username}"]
    assert utils.sort_routes(routes) == expected

    routes = [
        "/users/{username}",
        "/users/me",
        "/users/{username}/items",
        "/users/{username}/items/{item}",
    ]
    expected = [
        "/users/me",
        "/users/{username}/items/{item}",
        "/users/{username}/items",
        "/users/{username}",
    ]
    assert utils.sort_routes(routes) == expected

    routes = [
        "/users/{username}",
        "/users/me",
        "/users/{username}/items/{item}",
        "/users/{username}/items/special",
    ]
    expected = [
        "/users/me",
        "/users/{username}/items/special",
        "/users/{username}/items/{item}",
        "/users/{username}",
    ]
    assert utils.sort_routes(routes) == expected


def test_sort_apis_by_basepath():
    api1 = MagicMock(base_path="/")
    api2 = MagicMock(base_path="/basepath")
    assert utils.sort_apis_by_basepath([api1, api2]) == [api2, api1]

    api3 = MagicMock(base_path="/basepath/v2")
    assert utils.sort_apis_by_basepath([api1, api2, api3]) == [api3, api2, api1]

    api4 = MagicMock(base_path="/healthz")
    assert utils.sort_apis_by_basepath([api1, api2, api3, api4]) == [
        api3,
        api2,
        api4,
        api1,
    ]
