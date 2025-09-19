#!/usr/bin/env python3
"""
Tests for security violation logging functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from server_lib.security import log_security_violation


def test_log_security_violation_basic():
    """Test basic security violation logging."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        # Test logging to file and stdout
        with patch('sys.stdout') as mock_stdout:
            log_security_violation("127.0.0.1:12345", "GET /../etc/passwd HTTP/1.1", "Path traversal detected", log_file)
        
        # Check file was written
        assert os.path.exists(log_file)
        with open(log_file, 'r') as f:
            content = f.read()
            assert "SECURITY VIOLATION" in content
            assert "127.0.0.1:12345" in content
            assert "GET /../etc/passwd HTTP/1.1" in content
            assert "Path traversal detected" in content
            assert "Z]" in content  # ISO timestamp with Z
        
        # Check stdout was called
        mock_stdout.write.assert_called()
        mock_stdout.flush.assert_called()
        
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


def test_log_security_violation_default_file():
    """Test that default security.log file is used when no file specified."""
    with patch('builtins.open') as mock_open:
        with patch('sys.stdout') as mock_stdout:
            log_security_violation("192.168.1.100:8080", "GET / HTTP/1.1", "Missing Host header")
        
        # Check that security.log was opened
        mock_open.assert_called_with("security.log", "a", encoding="utf-8")


def test_log_security_violation_file_write_error():
    """Test handling of file write errors."""
    with patch('builtins.open', side_effect=IOError("Permission denied")):
        with patch('sys.stderr') as mock_stderr:
            with patch('sys.stdout') as mock_stdout:
                log_security_violation("10.0.0.1:9999", "POST /upload HTTP/1.1", "Invalid Host header")
        
        # Should still write to stdout
        mock_stdout.write.assert_called()
        mock_stdout.flush.assert_called()
        
        # Should log error to stderr
        mock_stderr.write.assert_called()
        # Check that the error message was written to stderr
        stderr_calls = [str(call) for call in mock_stderr.write.call_args_list]
        assert any("WARNING: Failed to write to security log file" in call for call in stderr_calls)


def test_log_security_violation_iso_timestamp():
    """Test that ISO timestamp format is correct."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        with patch('sys.stdout'):
            log_security_violation("127.0.0.1:12345", "GET / HTTP/1.1", "Test violation", log_file)
        
        with open(log_file, 'r') as f:
            content = f.read()
            # Check ISO timestamp format: YYYY-MM-DDTHH:MM:SS.ffffffZ
            assert content.startswith('[')
            assert 'Z]' in content
            # Should have proper structure
            assert 'SECURITY VIOLATION' in content
        
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


def test_log_security_violation_format():
    """Test the exact format of log entries."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        with patch('sys.stdout'):
            log_security_violation("192.168.1.50:4567", "GET /admin HTTP/1.1", "Unauthorized access attempt", log_file)
        
        with open(log_file, 'r') as f:
            content = f.read().strip()
            
        # Should match pattern: [timestamp] SECURITY VIOLATION - client - request - reason
        # The actual format is: [timestamp] SECURITY VIOLATION - client - request - reason
        assert content.startswith('[')
        assert 'Z] SECURITY VIOLATION' in content
        assert '192.168.1.50:4567' in content
        assert 'GET /admin HTTP/1.1' in content
        assert 'Unauthorized access attempt' in content
        
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


def test_log_security_violation_special_characters():
    """Test logging with special characters in request and reason."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        with patch('sys.stdout'):
            # Test with special characters that might cause issues
            log_security_violation(
                "127.0.0.1:12345", 
                "GET /path with spaces & symbols?param=value HTTP/1.1", 
                "Reason with \"quotes\" and 'apostrophes' and \n newlines",
                log_file
            )
        
        with open(log_file, 'r') as f:
            content = f.read()
            assert "path with spaces & symbols" in content
            assert "quotes" in content
            assert "apostrophes" in content
            # Newlines should be preserved in the log
            assert "\n" in content
        
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


def test_log_security_violation_multiple_entries():
    """Test that multiple log entries are written correctly."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        with patch('sys.stdout'):
            # Write multiple entries
            log_security_violation("127.0.0.1:1111", "GET / HTTP/1.1", "Violation 1", log_file)
            log_security_violation("127.0.0.1:2222", "POST /upload HTTP/1.1", "Violation 2", log_file)
            log_security_violation("127.0.0.1:3333", "GET /admin HTTP/1.1", "Violation 3", log_file)
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        assert len(lines) == 3
        for i, line in enumerate(lines, 1):
            assert f"Violation {i}" in line
            assert "SECURITY VIOLATION" in line
        
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)
