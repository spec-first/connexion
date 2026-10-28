from urllib.parse import quote_plus

import pytest
from connexion.uri_parsing import (
    AlwaysMultiURIParser,
    FirstValueURIParser,
    OpenAPIURIParser,
    Swagger2URIParser,
)
from starlette.datastructures import QueryParams
from werkzeug.datastructures import MultiDict

QUERY1 = MultiDict([("letters", "a"), ("letters", "b,c"), ("letters", "d,e,f")])
QUERY2 = MultiDict([("letters", "a"), ("letters", "b|c"), ("letters", "d|e|f")])

QUERY3 = MultiDict(
    [
        ("letters[eq]", ["a"]),
        ("letters[eq]", ["b", "c"]),
        ("letters[eq]", ["d", "e", "f"]),
    ]
)
QUERY4 = MultiDict(
    [("letters[eq]", "a"), ("letters[eq]", "b|c"), ("letters[eq]", "d|e|f")]
)
QUERY5 = MultiDict(
    [("letters[eq]", "a"), ("letters[eq]", "b,c"), ("letters[eq]", "d,e,f")]
)

QUERY6 = MultiDict([("letters_eq", "a")])
PATH1 = {"letters": "d,e,f"}
PATH2 = {"letters": "d|e|f"}
CSV = "csv"
PIPES = "pipes"
MULTI = "multi"


@pytest.mark.parametrize(
    "parser_class, expected, query_in, collection_format",
    [
        (Swagger2URIParser, ["d", "e", "f"], QUERY1, CSV),
        (FirstValueURIParser, ["a"], QUERY1, CSV),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, CSV),
        (Swagger2URIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, MULTI),
        (FirstValueURIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, MULTI),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, MULTI),
        (Swagger2URIParser, ["d", "e", "f"], QUERY2, PIPES),
        (FirstValueURIParser, ["a"], QUERY2, PIPES),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY2, PIPES),
    ],
)
async def test_uri_parser_query_params(
    parser_class, expected, query_in, collection_format
):
    class Request:
        query = query_in
        path_params = {}
        form = {}

    request = Request()
    parameters = [
        {
            "name": "letters",
            "in": "query",
            "type": "array",
            "items": {"type": "string"},
            "collectionFormat": collection_format,
        }
    ]
    body_defn = {}
    parser = parser_class(parameters, body_defn)
    res = parser.resolve_query(request.query.to_dict(flat=False))
    assert res["letters"] == expected


@pytest.mark.parametrize(
    "parser_class, expected, query_in, collection_format",
    [
        (Swagger2URIParser, ["d", "e", "f"], QUERY1, CSV),
        (FirstValueURIParser, ["a"], QUERY1, CSV),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, CSV),
        (Swagger2URIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, MULTI),
        (FirstValueURIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, MULTI),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY1, MULTI),
        (Swagger2URIParser, ["d", "e", "f"], QUERY2, PIPES),
        (FirstValueURIParser, ["a"], QUERY2, PIPES),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY2, PIPES),
    ],
)
async def test_uri_parser_form_params(
    parser_class, expected, query_in, collection_format
):
    class Request:
        query = {}
        form = query_in
        path_params = {}

    request = Request()
    parameters = [
        {
            "name": "letters",
            "in": "formData",
            "type": "array",
            "items": {"type": "string"},
            "collectionFormat": collection_format,
        }
    ]
    body_defn = {}
    parser = parser_class(parameters, body_defn)
    res = parser.resolve_form(request.form.to_dict(flat=False))
    assert res["letters"] == expected


@pytest.mark.parametrize(
    "parser_class, expected, query_in, collection_format",
    [
        (Swagger2URIParser, ["d", "e", "f"], PATH1, CSV),
        (FirstValueURIParser, ["d", "e", "f"], PATH1, CSV),
        (AlwaysMultiURIParser, ["d", "e", "f"], PATH1, CSV),
        (Swagger2URIParser, ["d", "e", "f"], PATH2, PIPES),
        (FirstValueURIParser, ["d", "e", "f"], PATH2, PIPES),
        (AlwaysMultiURIParser, ["d", "e", "f"], PATH2, PIPES),
    ],
)
async def test_uri_parser_path_params(
    parser_class, expected, query_in, collection_format
):
    class Request:
        query = {}
        form = {}
        path_params = query_in

    request = Request()
    parameters = [
        {
            "name": "letters",
            "in": "path",
            "type": "array",
            "items": {"type": "string"},
            "collectionFormat": collection_format,
        }
    ]
    body_defn = {}
    parser = parser_class(parameters, body_defn)
    res = parser.resolve_path(request.path_params)
    assert res["letters"] == expected


@pytest.mark.parametrize(
    "parser_class, expected, query_in, collection_format",
    [
        (OpenAPIURIParser, ["d", "e", "f"], QUERY3, None),
        (Swagger2URIParser, ["d", "e", "f"], QUERY5, CSV),
        (FirstValueURIParser, ["a"], QUERY5, CSV),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY5, CSV),
        (Swagger2URIParser, ["d", "e", "f"], QUERY4, PIPES),
        (FirstValueURIParser, ["a"], QUERY4, PIPES),
        (AlwaysMultiURIParser, ["a", "b", "c", "d", "e", "f"], QUERY4, PIPES),
    ],
)
async def test_uri_parser_query_params_with_square_brackets(
    parser_class, expected, query_in, collection_format
):
    class Request:
        query = query_in
        path_params = {}
        form = {}

    request = Request()
    parameters = [
        {
            "name": "letters[eq]",
            "in": "query",
            "type": "array",
            "items": {"type": "string"},
            "collectionFormat": collection_format,
        }
    ]
    body_defn = {}
    parser = parser_class(parameters, body_defn)
    res = parser.resolve_query(request.query.to_dict(flat=False))
    assert res["letters[eq]"] == expected


@pytest.mark.parametrize(
    "parser_class, expected, query_in, collection_format",
    [
        (OpenAPIURIParser, ["a"], QUERY6, CSV),
        (Swagger2URIParser, ["a"], QUERY6, CSV),
        (FirstValueURIParser, ["a"], QUERY6, CSV),
        (AlwaysMultiURIParser, ["a"], QUERY6, CSV),
        (Swagger2URIParser, ["a"], QUERY6, MULTI),
        (FirstValueURIParser, ["a"], QUERY6, MULTI),
        (AlwaysMultiURIParser, ["a"], QUERY6, MULTI),
        (Swagger2URIParser, ["a"], QUERY6, PIPES),
        (FirstValueURIParser, ["a"], QUERY6, PIPES),
        (AlwaysMultiURIParser, ["a"], QUERY6, PIPES),
    ],
)
async def test_uri_parser_query_params_with_underscores(
    parser_class, expected, query_in, collection_format
):
    class Request:
        query = query_in
        path_params = {}
        form = {}

    request = Request()
    parameters = [
        {
            "name": "letters",
            "in": "query",
            "type": "string",
            "items": {"type": "string"},
            "collectionFormat": collection_format,
        }
    ]
    body_defn = {}
    parser = parser_class(parameters, body_defn)
    res = parser.resolve_query(request.query.to_dict(flat=False))
    assert res["letters_eq"] == expected


@pytest.mark.parametrize(
    "parser_class, query_in, collection_format, explode, expected",
    [
        (
            OpenAPIURIParser,
            MultiDict([("letters[eq]_unrelated", "a")]),
            None,
            False,
            {"letters[eq]_unrelated": ["a"]},
        ),
        (
            OpenAPIURIParser,
            MultiDict([("letters[eq][unrelated]", "a")]),
            "csv",
            True,
            {"letters[eq][unrelated]": ["a"]},
        ),
    ],
)
async def test_uri_parser_query_params_with_malformed_names(
    parser_class, query_in, collection_format, explode, expected
):
    class Request:
        query = query_in
        path_params = {}
        form = {}

    request = Request()
    parameters = [
        {
            "name": "letters[eq]",
            "in": "query",
            "explode": explode,
            "collectionFormat": collection_format,
            "schema": {
                "type": "array",
                "items": {"type": "string"},
            },
        }
    ]
    body_defn = {}
    parser = parser_class(parameters, body_defn)
    res = parser.resolve_query(request.query.to_dict(flat=False))
    assert res == expected


def test_parameter_coercion():
    params = [
        {"name": "p1", "in": "path", "type": "integer", "required": True},
        {"name": "h1", "in": "header", "type": "string", "enum": ["a", "b"]},
        {"name": "q1", "in": "query", "type": "integer", "maximum": 3},
        {
            "name": "a1",
            "in": "query",
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {"type": "integer", "minimum": 0},
        },
    ]

    uri_parser = Swagger2URIParser(params, {})

    parsed_param = uri_parser.resolve_path({"p1": "123"})
    assert parsed_param == {"p1": 123}

    parsed_param = uri_parser.resolve_path({"p1": ""})
    assert parsed_param == {"p1": ""}

    parsed_param = uri_parser.resolve_path({"p1": "foo"})
    assert parsed_param == {"p1": "foo"}

    parsed_param = uri_parser.resolve_path({"p1": "1.2"})
    assert parsed_param == {"p1": "1.2"}

    parsed_param = uri_parser.resolve_path({"p1": 1})
    assert parsed_param == {"p1": 1}

    parsed_param = uri_parser.resolve_query(QueryParams("q1=4"))
    assert parsed_param == {"q1": 4}

    parsed_param = uri_parser.resolve_query(QueryParams("q1=3"))
    assert parsed_param == {"q1": 3}

    parsed_param = uri_parser.resolve_query(QueryParams(f"a1={quote_plus('1,2')}"))
    assert parsed_param == {"a1": [2]}  # Swagger2URIParser

    parsed_param = uri_parser.resolve_query(QueryParams(f"a1={quote_plus('1,a')}"))
    assert parsed_param == {"a1": ["a"]}  # Swagger2URIParser

    parsed_param = uri_parser.resolve_query(QueryParams(f"a1={quote_plus('1,-1')}"))
    assert parsed_param == {"a1": [1]}  # Swagger2URIParser

    parsed_param = uri_parser.resolve_query(QueryParams(f"a1=1"))
    assert parsed_param == {"a1": [1]}  # Swagger2URIParser

    parsed_param = uri_parser.resolve_query(QueryParams(f"a1={quote_plus('1,2,3,4')}"))
    assert parsed_param == {"a1": [4]}  # Swagger2URIParser


OBJECT_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "num": {"type": "integer"}},
}


@pytest.mark.parametrize(
    "param, query_in, expected",
    [
        # style=form, explode=true (default): one query parameter per property
        (
            {"name": "obj", "in": "query", "schema": OBJECT_SCHEMA},
            {"name": ["hello"], "num": ["1"]},
            {"obj": {"name": "hello", "num": 1}},
        ),
        # style=form, explode=false: a single k,v,k,v value
        (
            {"name": "obj", "in": "query", "explode": False, "schema": OBJECT_SCHEMA},
            {"obj": ["name,hello,num,1"]},
            {"obj": {"name": "hello", "num": 1}},
        ),
        # malformed values are left for validation
        (
            {"name": "obj", "in": "query", "explode": False, "schema": OBJECT_SCHEMA},
            {"obj": ["name,hello,num"]},
            {"obj": "name,hello,num"},
        ),
    ],
)
def test_uri_parser_query_form_object(param, query_in, expected):
    parser = OpenAPIURIParser([param], {})
    assert parser.resolve_query(query_in) == expected


def test_uri_parser_query_form_object_keeps_declared_params():
    # a property key that is also a parameter of its own is passed to both
    parameters = [
        {"name": "obj", "in": "query", "schema": OBJECT_SCHEMA},
        {"name": "num", "in": "query", "schema": {"type": "integer"}},
    ]
    parser = OpenAPIURIParser(parameters, {})
    res = parser.resolve_query({"name": ["hello"], "num": ["1"]})
    assert res == {"obj": {"name": "hello", "num": 1}, "num": 1}


@pytest.mark.parametrize(
    "param, headers, expected",
    [
        (
            {"name": "X-Rate", "in": "header", "schema": {"type": "integer"}},
            {"x-rate": "5"},
            {"X-Rate": 5},
        ),
        (
            {
                "name": "X-Ids",
                "in": "header",
                "schema": {"type": "array", "items": {"type": "integer"}},
            },
            {"X-Ids": "1,2,3"},
            {"X-Ids": [1, 2, 3]},
        ),
        (
            {"name": "X-Obj", "in": "header", "schema": OBJECT_SCHEMA},
            {"X-Obj": "name,hello,num,1"},
            {"X-Obj": {"name": "hello", "num": 1}},
        ),
        (
            {"name": "X-Obj", "in": "header", "explode": True, "schema": OBJECT_SCHEMA},
            {"X-Obj": "name=hello,num=1"},
            {"X-Obj": {"name": "hello", "num": 1}},
        ),
        # malformed values are left for validation
        (
            {"name": "X-Obj", "in": "header", "schema": OBJECT_SCHEMA},
            {"X-Obj": "name,hello,num"},
            {"X-Obj": "name,hello,num"},
        ),
        # headers that are not defined as parameters are not included
        (
            {"name": "X-Rate", "in": "header", "schema": {"type": "integer"}},
            {"X-Other": "1"},
            {},
        ),
    ],
)
def test_uri_parser_headers(param, headers, expected):
    parser = OpenAPIURIParser([param], {})
    assert parser.resolve_headers(headers) == expected


def test_uri_parser_header_and_query_with_same_name():
    parameters = [
        {"name": "id", "in": "query", "schema": {"type": "string"}},
        {"name": "id", "in": "header", "schema": {"type": "integer"}},
    ]
    parser = OpenAPIURIParser(parameters, {})
    assert parser.resolve_query({"id": ["abc"]}) == {"id": "abc"}
    assert parser.resolve_headers({"id": "3"}) == {"id": 3}


def test_uri_parser_repeated_headers():
    from starlette.datastructures import Headers

    parameters = [
        {
            "name": "X-Ids",
            "in": "header",
            "schema": {"type": "array", "items": {"type": "integer"}},
        },
        {"name": "X-Rate", "in": "header", "schema": {"type": "integer"}},
    ]
    parser = OpenAPIURIParser(parameters, {})
    headers = Headers(
        raw=[
            (b"x-ids", b"1,2"),
            (b"x-ids", b"3"),
            (b"x-rate", b"5"),
            (b"x-rate", b"6"),
        ]
    )
    # repeated lines of an array header are combined; otherwise the first line is
    # used, like headers.get()
    assert parser.resolve_headers(headers) == {"X-Ids": [1, 2, 3], "X-Rate": 5}


def test_uri_parser_swagger2_header_collection_format():
    parameters = [
        {
            "name": "X-Ids",
            "in": "header",
            "type": "array",
            "collectionFormat": "pipes",
            "items": {"type": "integer"},
        }
    ]
    parser = Swagger2URIParser(parameters, {})
    assert parser.resolve_headers({"X-Ids": "1|2"}) == {"X-Ids": [1, 2]}


def test_uri_parser_query_form_object_property_named_like_path_param():
    # a consumed property key that is only a *path* parameter is not kept as a query
    # parameter (it would be reported as unknown with strict_validation)
    parameters = [
        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
        {
            "name": "obj",
            "in": "query",
            "schema": {"type": "object", "properties": {"id": {"type": "string"}}},
        },
    ]
    parser = OpenAPIURIParser(parameters, {})
    assert parser.resolve_query({"id": ["x"]}) == {"obj": {"id": "x"}}
