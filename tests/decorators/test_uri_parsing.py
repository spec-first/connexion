import pytest
from connexion.decorators.uri_parsing import (AlwaysMultiURIParser,
                                              FirstValueURIParser,
                                              OpenAPIURIParser,
                                              Swagger2URIParser)
from werkzeug.datastructures import MultiDict

QUERY1 = MultiDict([("letters", "a"), ("letters", "b,c"),
                    ("letters", "d,e,f")])
QUERY2 = MultiDict([("letters", "a"), ("letters", "b|c"),
                    ("letters", "d|e|f")])
QUERY3 = MultiDict([("letters[eq]", ["a"]), ("letters[eq]", ["b", "c"]),
                    ("letters[eq]", ["d", "e", "f"])])
QUERY4 = MultiDict([("letters[eq]", "a"), ("letters[eq]", "b|c"),
                    ("letters[eq]", "d|e|f")])
QUERY5 = MultiDict([("letters[eq]", "a"), ("letters[eq]", "b,c"),
                    ("letters[eq]", "d,e,f")])
PATH1 = {"letters": "d,e,f"}
PATH2 = {"letters": "d|e|f"}
CSV = "csv"
PIPES = "pipes"
MULTI = "multi"


@pytest.mark.parametrize("parser_class, expected, query_in, collection_format", [
        (Swagger2URIParser, ['d', 'e', 'f'], QUERY1, CSV),
        (FirstValueURIParser, ['a'], QUERY1, CSV),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, CSV),
        (Swagger2URIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, MULTI),
        (FirstValueURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, MULTI),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, MULTI),
        (Swagger2URIParser, ['d', 'e', 'f'], QUERY2, PIPES),
        (FirstValueURIParser, ['a'], QUERY2, PIPES),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY2, PIPES)])
def test_uri_parser_query_params(parser_class, expected, query_in, collection_format):
    class Request:
        query = query_in
        path_params = {}
        form = {}

    request = Request()
    parameters = [
        {"name": "letters",
         "in": "query",
         "type": "array",
         "items": {"type": "string"},
         "collectionFormat": collection_format}
    ]
    body_defn = {}
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.query["letters"] == expected


@pytest.mark.parametrize("parser_class, expected, query_in, collection_format", [
        (Swagger2URIParser, ['d', 'e', 'f'], QUERY1, CSV),
        (FirstValueURIParser, ['a'], QUERY1, CSV),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, CSV),
        (Swagger2URIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, MULTI),
        (FirstValueURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, MULTI),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY1, MULTI),
        (Swagger2URIParser, ['d', 'e', 'f'], QUERY2, PIPES),
        (FirstValueURIParser, ['a'], QUERY2, PIPES),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY2, PIPES)])
def test_uri_parser_form_params(parser_class, expected, query_in, collection_format):
    class Request:
        query = {}
        form = query_in
        path_params = {}

    request = Request()
    parameters = [
        {"name": "letters",
         "in": "formData",
         "type": "array",
         "items": {"type": "string"},
         "collectionFormat": collection_format}
    ]
    body_defn = {}
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.form["letters"] == expected


@pytest.mark.parametrize("parser_class, expected, query_in, collection_format", [
        (Swagger2URIParser, ['d', 'e', 'f'], PATH1, CSV),
        (FirstValueURIParser, ['d', 'e', 'f'], PATH1, CSV),
        (AlwaysMultiURIParser, ['d', 'e', 'f'], PATH1, CSV),
        (Swagger2URIParser, ['d', 'e', 'f'], PATH2, PIPES),
        (FirstValueURIParser, ['d', 'e', 'f'], PATH2, PIPES),
        (AlwaysMultiURIParser, ['d', 'e', 'f'], PATH2, PIPES)])
def test_uri_parser_path_params(parser_class, expected, query_in, collection_format):
    class Request:
        query = {}
        form = {}
        path_params = query_in

    request = Request()
    parameters = [
        {"name": "letters",
         "in": "path",
         "type": "array",
         "items": {"type": "string"},
         "collectionFormat": collection_format}
    ]
    body_defn = {}
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.path_params["letters"] == expected


@pytest.mark.parametrize("parser_class, expected, query_in, collection_format", [
        (OpenAPIURIParser, ['d', 'e', 'f'], QUERY3, None),
        (Swagger2URIParser, ['d', 'e', 'f'], QUERY5, CSV),
        (FirstValueURIParser, ['a'], QUERY5, CSV),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY5, CSV),
        (Swagger2URIParser, ['d', 'e', 'f'], QUERY4, PIPES),
        (FirstValueURIParser, ['a'], QUERY4, PIPES),
        (AlwaysMultiURIParser, ['a', 'b', 'c', 'd', 'e', 'f'], QUERY4, PIPES)])
def test_uri_parser_query_params_with_square_brackets(parser_class, expected, query_in, collection_format):
    class Request:
        query = query_in
        path_params = {}
        form = {}

    request = Request()
    parameters = [
        {"name": "letters[eq]",
         "in": "query",
         "type": "array",
         "items": {"type": "string"},
         "collectionFormat": collection_format}
    ]
    body_defn = {}
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.query["letters[eq]"] == expected
