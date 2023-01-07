from connexion.frameworks import flask as flask_utils


def test_flaskify_path():
    assert flask_utils.flaskify_path("{test-path}") == "<test_path>"
    assert flask_utils.flaskify_path("api/{test-path}") == "api/<test_path>"
    assert flask_utils.flaskify_path("my-api/{test-path}") == "my-api/<test_path>"
    assert flask_utils.flaskify_path("foo_bar/{a-b}/{c_d}") == "foo_bar/<a_b>/<c_d>"
    assert (
        flask_utils.flaskify_path("foo/{a}/{b}", {"a": "integer"}) == "foo/<int:a>/<b>"
    )
    assert (
        flask_utils.flaskify_path("foo/{a}/{b}", {"a": "number"}) == "foo/<float:a>/<b>"
    )
    assert flask_utils.flaskify_path("foo/{a}/{b}", {"a": "path"}) == "foo/<path:a>/<b>"
    assert flask_utils.flaskify_path("foo/{a}", {"a": "path"}) == "foo/<path:a>"


def test_flaskify_endpoint():
    assert flask_utils.flaskify_endpoint("module.function") == "module_function"
    assert flask_utils.flaskify_endpoint("function") == "function"

    name = "module.function"
    randlen = 6
    res = flask_utils.flaskify_endpoint(name, randlen)
    assert res.startswith("module_function")
    assert len(res) == len(name) + 1 + randlen
