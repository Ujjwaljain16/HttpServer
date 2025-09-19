#!/usr/bin/env python3
"""
Tests for standardized error response functions.
"""

import pytest
from server_lib.response import make_error_response, make_method_not_allowed_response


def test_make_error_response_basic():
    """Test basic error response creation."""
    response = make_error_response(400, "Bad Request", "Invalid request")
    
    # Check it's bytes
    assert isinstance(response, bytes)
    
    # Decode and check structure
    response_str = response.decode('latin-1')
    lines = response_str.split('\r\n')
    
    # Check status line
    assert lines[0] == "HTTP/1.1 400 Bad Request"
    
    # Check required headers
    assert any("Date:" in line for line in lines)
    assert any("Server: Multi-threaded HTTP Server" in line for line in lines)
    assert any("Content-Type: text/plain; charset=utf-8" in line for line in lines)
    assert any("Content-Length:" in line for line in lines)
    
    # Check body
    assert "Invalid request" in response_str


def test_make_error_response_close_connection():
    """Test error response with connection close."""
    response = make_error_response(403, "Forbidden", "Access denied", close_connection=True)
    response_str = response.decode('latin-1')
    
    assert "Connection: close" in response_str
    assert "Keep-Alive:" not in response_str


def test_make_error_response_keep_alive():
    """Test error response with keep-alive."""
    response = make_error_response(404, "Not Found", "Resource not found", close_connection=False)
    response_str = response.decode('latin-1')
    
    assert "Connection: keep-alive" in response_str
    assert "Keep-Alive: timeout=30, max=100" in response_str


def test_make_error_response_utf8_body():
    """Test error response with UTF-8 body."""
    body_text = "Error with special chars: éñ中文🚀"
    response = make_error_response(500, "Internal Server Error", body_text)
    
    # Decode headers as latin-1, but body as utf-8
    response_str = response.decode('latin-1')
    header_end = response_str.find('\r\n\r\n')
    headers = response_str[:header_end]
    body = response[header_end + 4:].decode('utf-8')
    
    assert body_text in body
    
    # Check Content-Length is correct
    for line in headers.split('\r\n'):
        if line.startswith('Content-Length:'):
            length = int(line.split(':')[1].strip())
            assert length == len(body_text.encode('utf-8'))


def test_make_error_response_various_status_codes():
    """Test various HTTP status codes."""
    test_cases = [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (405, "Method Not Allowed"),
        (415, "Unsupported Media Type"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
    ]
    
    for status_code, reason in test_cases:
        response = make_error_response(status_code, reason, f"Test {status_code}")
        response_str = response.decode('latin-1')
        
        assert f"HTTP/1.1 {status_code} {reason}" in response_str


def test_make_method_not_allowed_response():
    """Test 405 Method Not Allowed response."""
    response = make_method_not_allowed_response(["GET", "POST"])
    response_str = response.decode('latin-1')
    
    # Check status line
    assert "HTTP/1.1 405 Method Not Allowed" in response_str
    
    # Check Allow header
    assert "Allow: GET, POST" in response_str
    
    # Check body
    assert "Method not allowed. Allowed methods: GET, POST" in response_str
    
    # Check other required headers
    assert "Content-Type: text/plain; charset=utf-8" in response_str
    assert "Content-Length:" in response_str


def test_make_method_not_allowed_response_single_method():
    """Test 405 response with single allowed method."""
    response = make_method_not_allowed_response(["GET"])
    response_str = response.decode('latin-1')
    
    assert "Allow: GET" in response_str
    assert "Method not allowed. Allowed methods: GET" in response_str


def test_make_method_not_allowed_response_multiple_methods():
    """Test 405 response with multiple allowed methods."""
    methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    response = make_method_not_allowed_response(methods)
    response_str = response.decode('latin-1')
    
    assert "Allow: GET, POST, PUT, DELETE, PATCH" in response_str
    assert "Method not allowed. Allowed methods: GET, POST, PUT, DELETE, PATCH" in response_str


def test_make_method_not_allowed_response_close_connection():
    """Test 405 response with connection close."""
    response = make_method_not_allowed_response(["GET", "POST"], close_connection=True)
    response_str = response.decode('latin-1')
    
    assert "Connection: close" in response_str
    assert "Keep-Alive:" not in response_str


def test_make_method_not_allowed_response_keep_alive():
    """Test 405 response with keep-alive."""
    response = make_method_not_allowed_response(["GET", "POST"], close_connection=False)
    response_str = response.decode('latin-1')
    
    assert "Connection: keep-alive" in response_str
    assert "Keep-Alive: timeout=30, max=100" in response_str


def test_error_response_headers_order():
    """Test that headers are in a reasonable order."""
    response = make_error_response(400, "Bad Request", "Test error")
    response_str = response.decode('latin-1')
    
    lines = response_str.split('\r\n')
    header_lines = [line for line in lines if ':' in line and not line.startswith('HTTP/')]
    
    # Check that required headers are present
    header_names = [line.split(':')[0] for line in header_lines]
    assert 'Date' in header_names
    assert 'Server' in header_names
    assert 'Content-Type' in header_names
    assert 'Content-Length' in header_names


def test_error_response_empty_body():
    """Test error response with empty body."""
    response = make_error_response(204, "No Content", "")
    response_str = response.decode('latin-1')
    
    # Should still have Content-Length: 0
    assert "Content-Length: 0" in response_str
    
    # Body should be empty
    assert response_str.endswith('\r\n\r\n')


def test_error_response_large_body():
    """Test error response with large body."""
    large_body = "x" * 10000
    response = make_error_response(500, "Internal Server Error", large_body)
    response_str = response.decode('latin-1')
    
    # Check Content-Length is correct
    for line in response_str.split('\r\n'):
        if line.startswith('Content-Length:'):
            length = int(line.split(':')[1].strip())
            assert length == len(large_body.encode('utf-8'))
    
    # Check body is included
    assert large_body in response_str
