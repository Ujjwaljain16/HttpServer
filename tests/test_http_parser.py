import socket
import types
import pytest

from server_lib.http_parser import (
    receive_http_request,
    parse_http_request,
    BadRequestError,
)


class FakeSocket:
    def __init__(self, chunks, delay_timeouts=False):
        self._chunks = list(chunks)
        self._timeout = None
    def settimeout(self, t):
        self._timeout = t
    def gettimeout(self):
        return self._timeout
    def recv(self, n):
        return self._chunks.pop(0) if self._chunks else b""


def test_receive_headers_multi_chunk():
    # Simulate split across multiple recv() calls
    s = FakeSocket([b"GET / HTTP/1.1\r\nHo", b"st: a\r\n\r\nEXTRA BODY".encode("latin-1")])
    data = receive_http_request(s, max_header_size=8192, timeout=1)
    assert data.endswith(b"\r\n\r\n")


def test_parse_valid_request_and_folded_headers():
    raw = (
        b"GET /index.html HTTP/1.1\r\n"
        b"Host: LocalHost:8080\r\n"
        b"X-Custom: value1\r\n\tcontinued\r\n"
        b"Connection: close\r\n\r\n"
    )
    method, path, version, headers = parse_http_request(raw)
    assert method == "GET"
    assert path == "/index.html"
    assert version == "HTTP/1.1"
    assert headers["host"] == "LocalHost:8080"
    assert headers["x-custom"] == "value1 continued"


def test_parse_malformed_request_line():
    raw = b"GET /index.html\r\nHost: a\r\n\r\n"
    with pytest.raises(BadRequestError):
        parse_http_request(raw)
