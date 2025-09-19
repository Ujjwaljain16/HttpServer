#!/usr/bin/env python3
"""
Tests for the detailed logging module.
"""

import json
import os
import tempfile
import threading
import time
import pytest
from pathlib import Path
from server_lib.logger import ServerLogger, setup_logging, get_logger, log_thread_status


def test_logger_basic_functionality():
    """Test basic logging functionality."""
    logger = ServerLogger("test", level=10)  # DEBUG level
    
    # Test all log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Should not raise any exceptions
    assert True


def test_logger_file_output():
    """Test logging to file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = ServerLogger("test", log_file=log_file, level=10)
        logger.info("Test message")
        logger.warning("Warning message")
        
        # Close logger to release file handle
        logger.close()
        
        # Read the log file
        with open(log_file, 'r') as f:
            content = f.read()
        
        assert "Test message" in content
        assert "Warning message" in content
        assert "INFO:" in content
        assert "WARNING:" in content
        
    finally:
        try:
            os.unlink(log_file)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


def test_logger_json_output():
    """Test JSON logging to file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json_file = f.name
    
    try:
        logger = ServerLogger("test", json_log_file=json_file, level=10)
        logger.info("Test message", extra_data={"key": "value"})
        logger.warning("Warning message", extra_data={"error_code": 500})
        
        # Close logger to release file handle
        logger.close()
        
        # Read the JSON log file
        with open(json_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        # Parse JSON lines
        log1 = json.loads(lines[0])
        log2 = json.loads(lines[1])
        
        assert log1["message"] == "Test message"
        assert log1["level"] == "INFO"
        assert log1["key"] == "value"
        assert "timestamp" in log1
        assert "thread_name" in log1
        
        assert log2["message"] == "Warning message"
        assert log2["level"] == "WARNING"
        assert log2["error_code"] == 500
        
    finally:
        try:
            os.unlink(json_file)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


def test_logger_thread_tracking():
    """Test thread tracking functionality."""
    logger = ServerLogger("test", level=10)
    
    # Register some threads
    logger.register_thread("worker-1", "worker", {"queue_size": 5})
    logger.register_thread("worker-2", "worker", {"queue_size": 3})
    logger.register_thread("main", "main", {"port": 8080})
    
    # Check thread stats
    stats = logger.get_thread_stats()
    assert stats["total_threads"] == 3
    assert stats["active_threads"] == 3
    assert stats["thread_types"]["worker"] == 2
    assert stats["thread_types"]["main"] == 1
    
    # Update thread status
    logger.update_thread_status("worker-1", "idle", {"processed": 10})
    stats = logger.get_thread_stats()
    assert stats["threads"]["worker-1"]["status"] == "idle"
    assert stats["threads"]["worker-1"]["info"]["processed"] == 10
    
    # Unregister thread
    logger.unregister_thread("worker-2")
    stats = logger.get_thread_stats()
    assert stats["total_threads"] == 2
    assert "worker-2" not in stats["threads"]


def test_logger_thread_context():
    """Test thread context manager."""
    logger = ServerLogger("test", level=10)
    
    with logger.thread_context("test-thread", "worker", {"test": True}):
        stats = logger.get_thread_stats()
        assert stats["total_threads"] == 1
        assert "test-thread" in stats["threads"]
        assert stats["threads"]["test-thread"]["type"] == "worker"
        assert stats["threads"]["test-thread"]["info"]["test"] is True
    
    # Thread should be unregistered after context
    stats = logger.get_thread_stats()
    assert stats["total_threads"] == 0


def test_logger_thread_status_logging():
    """Test thread status logging."""
    logger = ServerLogger("test", level=10)
    
    # Register some threads
    logger.register_thread("worker-1", "worker")
    logger.register_thread("worker-2", "worker")
    logger.register_thread("main", "main")
    
    # Update one thread to idle
    logger.update_thread_status("worker-1", "idle")
    
    # This should not raise an exception
    logger.log_thread_status()


def test_global_logger():
    """Test global logger functionality."""
    # Test get_logger
    logger1 = get_logger("test1")
    logger2 = get_logger("test2")
    
    assert logger1 is not None
    assert logger2 is not None
    
    # Test setup_logging
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = setup_logging(log_file=log_file, level=10)
        assert logger is not None
        assert logger.log_file == log_file
        
        # Close logger to release file handle
        logger.close()
        
    finally:
        try:
            os.unlink(log_file)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


def test_logger_convenience_functions():
    """Test convenience functions."""
    # These should not raise exceptions
    from server_lib.logger import debug, info, warning, error, critical
    
    debug("Debug message")
    info("Info message")
    warning("Warning message")
    error("Error message")
    critical("Critical message")
    
    # Test with extra data
    info("Info with data", extra_data={"key": "value"})
    
    assert True


def test_logger_thread_name_format():
    """Test that thread names are properly formatted in logs."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = ServerLogger("test", log_file=log_file, level=10)
        
        # Log from different threads
        def worker_thread():
            logger.info("Message from worker thread")
        
        thread = threading.Thread(target=worker_thread, name="worker-1")
        thread.start()
        thread.join()
        
        # Close logger to release file handle
        logger.close()
        
        # Read the log file
        with open(log_file, 'r') as f:
            content = f.read()
        
        assert "[worker-1]" in content
        assert "Message from worker thread" in content
        
    finally:
        try:
            os.unlink(log_file)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


def test_logger_timestamp_format():
    """Test that timestamps are properly formatted."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = ServerLogger("test", log_file=log_file, level=10)
        logger.info("Test message")
        
        # Close logger to release file handle
        logger.close()
        
        # Read the log file
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Check timestamp format [YYYY-MM-DD HH:MM:SS]
        import re
        timestamp_pattern = r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]'
        assert re.search(timestamp_pattern, content) is not None
        
    finally:
        try:
            os.unlink(log_file)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


def test_logger_json_timestamp_format():
    """Test that JSON logs have proper ISO timestamps."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json_file = f.name
    
    try:
        logger = ServerLogger("test", json_log_file=json_file, level=10)
        logger.info("Test message")
        
        # Close logger to release file handle
        logger.close()
        
        # Read the JSON log file
        with open(json_file, 'r') as f:
            content = f.read()
        
        log_entry = json.loads(content.strip())
        
        # Check timestamp format (ISO format with Z)
        assert log_entry["timestamp"].endswith("Z")
        assert "T" in log_entry["timestamp"]
        
    finally:
        try:
            os.unlink(json_file)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


def test_logger_cleanup():
    """Test logger cleanup functionality."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json_file = f.name
    
    try:
        logger = ServerLogger("test", json_log_file=json_file, level=10)
        logger.info("Test message")
        
        # Close logger
        logger.close()
        
        # Should not raise exception when logging after close
        logger.info("Message after close")
        
    finally:
        if os.path.exists(json_file):
            os.unlink(json_file)


def test_logger_error_handling():
    """Test error handling in JSON logging."""
    # Create a logger with invalid JSON file path
    logger = ServerLogger("test", json_log_file="/invalid/path/file.json", level=10)
    
    # Should not raise exception
    logger.info("Test message")
    
    # Cleanup
    logger.close()


def test_logger_multiple_instances():
    """Test multiple logger instances."""
    logger1 = ServerLogger("test1", level=10)
    logger2 = ServerLogger("test2", level=10)
    
    # Should be independent
    logger1.register_thread("thread1", "worker")
    logger2.register_thread("thread2", "worker")
    
    stats1 = logger1.get_thread_stats()
    stats2 = logger2.get_thread_stats()
    
    assert stats1["total_threads"] == 1
    assert stats2["total_threads"] == 1
    assert "thread1" in stats1["threads"]
    assert "thread2" in stats2["threads"]
    
    # Cleanup
    logger1.close()
    logger2.close()
