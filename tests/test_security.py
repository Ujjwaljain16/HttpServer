from pathlib import Path
import pytest
import logging

from server_lib.security import (
    safe_resolve_path, 
    validate_host_header,
    ForbiddenError,
    HostMissingError,
    HostMismatchError
)


def test_safe_resolve_ok(tmp_path: Path):
    resources = tmp_path / "resources"
    target = resources / "sub" / "file.txt"
    target.parent.mkdir(parents=True)
    target.write_text("x")
    resolved = safe_resolve_path("sub/file.txt", resources)
    assert resolved == target.resolve()


def test_safe_resolve_traversal(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir(parents=True)
    with pytest.raises(ForbiddenError):
        safe_resolve_path("../etc/passwd", resources)


def test_safe_resolve_percent_encoded_traversal(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir(parents=True)
    with pytest.raises(ForbiddenError):
        safe_resolve_path("..%2f..%2fetc/passwd", resources)


def test_safe_resolve_absolute_windows_drive(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir(parents=True)
    with pytest.raises(ForbiddenError):
        safe_resolve_path("C:/Windows/system32", resources)


# Host header validation tests
def test_validate_host_header_missing():
    """Test that missing Host header raises HostMissingError."""
    with pytest.raises(HostMissingError, match="Missing Host header"):
        validate_host_header({}, "127.0.0.1", 8080)


def test_validate_host_header_valid_localhost():
    """Test valid localhost variants."""
    # Test localhost without port
    assert validate_host_header({"host": "localhost"}, "127.0.0.1", 8080) is True
    
    # Test localhost with port
    assert validate_host_header({"host": "localhost:8080"}, "127.0.0.1", 8080) is True
    
    # Test 127.0.0.1 without port
    assert validate_host_header({"host": "127.0.0.1"}, "127.0.0.1", 8080) is True
    
    # Test 127.0.0.1 with port
    assert validate_host_header({"host": "127.0.0.1:8080"}, "127.0.0.1", 8080) is True


def test_validate_host_header_valid_server_host():
    """Test valid server host."""
    assert validate_host_header({"host": "example.com"}, "example.com", 8080) is True
    assert validate_host_header({"host": "example.com:8080"}, "example.com", 8080) is True


def test_validate_host_header_invalid_host():
    """Test invalid host names."""
    with pytest.raises(HostMismatchError, match="Host header 'evil.com' not allowed"):
        validate_host_header({"host": "evil.com"}, "127.0.0.1", 8080)
    
    with pytest.raises(HostMismatchError, match="Host header 'malicious.com' not allowed"):
        validate_host_header({"host": "malicious.com"}, "127.0.0.1", 8080)


def test_validate_host_header_invalid_port():
    """Test invalid port numbers."""
    with pytest.raises(HostMismatchError, match="Host header port 9000 doesn't match server port 8080"):
        validate_host_header({"host": "localhost:9000"}, "127.0.0.1", 8080)
    
    with pytest.raises(HostMismatchError, match="Invalid Host header port"):
        validate_host_header({"host": "localhost:invalid"}, "127.0.0.1", 8080)


def test_validate_host_header_case_insensitive():
    """Test that Host header is case-insensitive."""
    assert validate_host_header({"host": "LOCALHOST"}, "127.0.0.1", 8080) is True
    assert validate_host_header({"host": "LocalHost:8080"}, "127.0.0.1", 8080) is True


def test_validate_host_header_bound_to_all_interfaces():
    """Test server bound to 0.0.0.0 (all interfaces)."""
    # Should accept localhost variants when bound to 0.0.0.0
    assert validate_host_header({"host": "localhost"}, "0.0.0.0", 8080) is True
    assert validate_host_header({"host": "127.0.0.1"}, "0.0.0.0", 8080) is True
    assert validate_host_header({"host": "0.0.0.0"}, "0.0.0.0", 8080) is True
    
    # Should reject external hosts
    with pytest.raises(HostMismatchError):
        validate_host_header({"host": "evil.com"}, "0.0.0.0", 8080)


def test_validate_host_header_ipv6():
    """Test IPv6 localhost."""
    # Should accept ::1 when bound to all interfaces
    assert validate_host_header({"host": "::1"}, "0.0.0.0", 8080) is True
    assert validate_host_header({"host": "[::1]:8080"}, "0.0.0.0", 8080) is True


def test_validate_host_header_logging(caplog):
    """Test that violations are logged."""
    with caplog.at_level(logging.WARNING):
        with pytest.raises(HostMissingError):
            validate_host_header({}, "127.0.0.1", 8080)
    
    assert "Request rejected: Missing Host header" in caplog.text
    
    with caplog.at_level(logging.WARNING):
        with pytest.raises(HostMismatchError):
            validate_host_header({"host": "evil.com"}, "127.0.0.1", 8080)
    
    assert "Request rejected: Host header 'evil.com' not in acceptable names" in caplog.text


def test_validate_host_header_debug_logging(caplog):
    """Test that successful validations are logged at debug level."""
    with caplog.at_level(logging.DEBUG):
        validate_host_header({"host": "localhost"}, "127.0.0.1", 8080)
    
    assert "Host header validation passed: 'localhost'" in caplog.text
