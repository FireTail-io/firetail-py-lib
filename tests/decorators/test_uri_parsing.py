import pytest
from werkzeug.datastructures import MultiDict

from firetail.decorators.uri_parsing import (
    AlwaysMultiURIParser,
    FirstValueURIParser,
    OpenAPIURIParser,
    Swagger2URIParser,
)

QUERY1 = MultiDict([("letters", "a"), ("letters", "b,c"), ("letters", "d,e,f")])
QUERY2 = MultiDict([("letters", "a"), ("letters", "b|c"), ("letters", "d|e|f")])

QUERY3 = MultiDict([("letters[eq]", ["a"]), ("letters[eq]", ["b", "c"]), ("letters[eq]", ["d", "e", "f"])])
QUERY4 = MultiDict([("letters[eq]", "a"), ("letters[eq]", "b|c"), ("letters[eq]", "d|e|f")])
QUERY5 = MultiDict([("letters[eq]", "a"), ("letters[eq]", "b,c"), ("letters[eq]", "d,e,f")])

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
def test_uri_parser_query_params(parser_class, expected, query_in, collection_format):
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
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.query["letters"] == expected


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
def test_uri_parser_form_params(parser_class, expected, query_in, collection_format):
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
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.form["letters"] == expected


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
def test_uri_parser_path_params(parser_class, expected, query_in, collection_format):
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
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.path_params["letters"] == expected


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
def test_uri_parser_query_params_with_square_brackets(parser_class, expected, query_in, collection_format):
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
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.query["letters[eq]"] == expected


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
def test_uri_parser_query_params_with_underscores(parser_class, expected, query_in, collection_format):
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
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.query["letters_eq"] == expected


@pytest.mark.parametrize(
    "parser_class, query_in, collection_format, explode, expected",
    [
        (OpenAPIURIParser, MultiDict([("letters[eq]_unrelated", "a")]), None, False, {"letters[eq]_unrelated": ["a"]}),
        (
            OpenAPIURIParser,
            MultiDict([("letters[eq][unrelated]", "a")]),
            "csv",
            True,
            {"letters[eq][unrelated]": ["a"]},
        ),
    ],
)
def test_uri_parser_query_params_with_malformed_names(parser_class, query_in, collection_format, explode, expected):
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
    p = parser_class(parameters, body_defn)
    res = p(lambda x: x)(request)
    assert res.query == expected
