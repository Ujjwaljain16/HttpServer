from server_lib.http_parser import parse_http_request, BadRequestError


def test_parse_valid_request():
    raw = (
        b"GET /index.html HTTP/1.1\r\n"
        b"Host: localhost:8080\r\n"
        b"Connection: close\r\n\r\n"
    )
    method, path, version, headers = parse_http_request(raw)
    assert method == "GET"
    assert path == "/index.html"
    assert version == "HTTP/1.1"
    assert headers["host"] == "localhost:8080"


def test_parse_malformed_request_line():
    raw = b"GET /index.html\r\nHost: a\r\n\r\n"
    try:
        parse_http_request(raw)
    except BadRequestError:
        pass
    else:
        assert False, "Expected BadRequestError"
