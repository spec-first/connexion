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
