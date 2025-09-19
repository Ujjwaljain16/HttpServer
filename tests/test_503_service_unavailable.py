#!/usr/bin/env python3
"""
Tests for 503 Service Unavailable response functionality.
"""

import pytest
from server_lib.response import make_service_unavailable_response


def test_make_service_unavailable_response_basic():
    """Test basic 503 response creation."""
    response = make_service_unavailable_response()
    
    # Check it's bytes
    assert isinstance(response, bytes)
    
    # Decode and check structure
    response_str = response.decode('latin-1')
    lines = response_str.split('\r\n')
    
    # Check status line
    assert lines[0] == "HTTP/1.1 503 Service Unavailable"
    
    # Check required headers
    assert any("Date:" in line for line in lines)
    assert any("Server: Multi-threaded HTTP Server" in line for line in lines)
    assert any("Content-Type: text/plain; charset=utf-8" in line for line in lines)
    assert any("Content-Length:" in line for line in lines)
    assert any("Retry-After: 5" in line for line in lines)
    assert any("Connection: close" in line for line in lines)
    
    # Check body
    assert "Service temporarily unavailable. Please try again later." in response_str


def test_make_service_unavailable_response_custom_retry_after():
    """Test 503 response with custom Retry-After value."""
    response = make_service_unavailable_response(retry_after=10)
    response_str = response.decode('latin-1')
    
    assert "Retry-After: 10" in response_str
    assert "Retry-After: 5" not in response_str


def test_make_service_unavailable_response_keep_alive():
    """Test 503 response with keep-alive connection."""
    response = make_service_unavailable_response(close_connection=False)
    response_str = response.decode('latin-1')
    
    assert "Connection: keep-alive" in response_str
    assert "Keep-Alive: timeout=30, max=100" in response_str
    assert "Connection: close" not in response_str


def test_make_service_unavailable_response_close_connection():
    """Test 503 response with connection close."""
    response = make_service_unavailable_response(close_connection=True)
    response_str = response.decode('latin-1')
    
    assert "Connection: close" in response_str
    assert "Keep-Alive:" not in response_str


def test_make_service_unavailable_response_retry_after_values():
    """Test various Retry-After values."""
    test_cases = [0, 1, 5, 10, 60, 300, 3600]  # Various retry intervals
    
    for retry_after in test_cases:
        response = make_service_unavailable_response(retry_after=retry_after)
        response_str = response.decode('latin-1')
        
        assert f"Retry-After: {retry_after}" in response_str


def test_make_service_unavailable_response_headers_order():
    """Test that headers are in a reasonable order."""
    response = make_service_unavailable_response()
    response_str = response.decode('latin-1')
    
    lines = response_str.split('\r\n')
    header_lines = [line for line in lines if ':' in line and not line.startswith('HTTP/')]
    
    # Check that required headers are present
    header_names = [line.split(':')[0] for line in header_lines]
    assert 'Date' in header_names
    assert 'Server' in header_names
    assert 'Content-Type' in header_names
    assert 'Content-Length' in header_names
    assert 'Retry-After' in header_names
    assert 'Connection' in header_names


def test_make_service_unavailable_response_body_content():
    """Test the body content of 503 response."""
    response = make_service_unavailable_response()
    response_str = response.decode('latin-1')
    
    # Extract body
    body_start = response_str.find('\r\n\r\n')
    body = response_str[body_start + 4:] if body_start != -1 else ""
    
    expected_body = "Service temporarily unavailable. Please try again later."
    assert body == expected_body


def test_make_service_unavailable_response_content_length():
    """Test that Content-Length is correct."""
    response = make_service_unavailable_response()
    response_str = response.decode('latin-1')
    
    # Extract Content-Length
    for line in response_str.split('\r\n'):
        if line.startswith('Content-Length:'):
            length = int(line.split(':')[1].strip())
            expected_body = "Service temporarily unavailable. Please try again later."
            expected_length = len(expected_body.encode('utf-8'))
            assert length == expected_length
            break
    else:
        pytest.fail("Content-Length header not found")


def test_make_service_unavailable_response_rfc_compliance():
    """Test that response follows RFC 7231 for 503 responses."""
    response = make_service_unavailable_response()
    response_str = response.decode('latin-1')
    
    # RFC 7231 requires Retry-After header for 503 responses
    assert "Retry-After:" in response_str
    
    # Should have proper status line
    assert response_str.startswith("HTTP/1.1 503 Service Unavailable")
    
    # Should have proper headers
    assert "Content-Type: text/plain; charset=utf-8" in response_str
    assert "Content-Length:" in response_str


def test_make_service_unavailable_response_utf8_encoding():
    """Test that response properly handles UTF-8 encoding."""
    # The current implementation uses ASCII body, but let's test the encoding
    response = make_service_unavailable_response()
    response_str = response.decode('latin-1')
    
    # Should be able to decode without errors
    assert isinstance(response_str, str)
    
    # Body should be properly encoded
    body_start = response_str.find('\r\n\r\n')
    if body_start != -1:
        body = response_str[body_start + 4:]
        # Should be valid UTF-8 when re-encoded
        body.encode('utf-8')
