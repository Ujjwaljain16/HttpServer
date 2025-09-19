#!/usr/bin/env python3
"""
Integration test for security violation logging.

This script tests that security violations are properly logged when
the server encounters malicious requests.
"""

import socket
import time
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_http_request(request: str, port: int = 8080) -> tuple[int, str]:
    """Send HTTP request and return response details."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    
    try:
        sock.connect(('127.0.0.1', port))
        sock.sendall(request.encode())
        
        # Read response
        response = b""
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk
            if b"\r\n\r\n" in response:
                break
        
        # Parse status code
        response_str = response.decode('latin-1')
        lines = response_str.split('\r\n')
        status_line = lines[0]
        status_code = int(status_line.split(' ', 2)[1])
        
        return status_code, response_str
        
    except Exception as e:
        return 0, f"Error: {e}"
    finally:
        sock.close()

def check_security_log(log_file: str = "security.log") -> list[str]:
    """Check security log file for entries."""
    if not os.path.exists(log_file):
        return []
    
    with open(log_file, 'r') as f:
        return f.readlines()

def test_security_logging():
    """Test various security violations and verify they are logged."""
    print("Testing security violation logging...")
    print("=" * 60)
    
    # Clear any existing security log
    if os.path.exists("security.log"):
        os.remove("security.log")
    
    test_cases = [
        # (request, expected_status, expected_reason, description)
        (
            "GET /../etc/passwd HTTP/1.1\r\nHost: localhost:8080\r\n\r\n",
            403,
            "Path traversal detected",
            "Path traversal attack"
        ),
        (
            "GET /..%2f..%2fetc/passwd HTTP/1.1\r\nHost: localhost:8080\r\n\r\n",
            403,
            "Path traversal detected",
            "Percent-encoded path traversal"
        ),
        (
            "GET / HTTP/1.1\r\n\r\n",  # Missing Host header
            400,
            "Missing Host header",
            "Missing Host header"
        ),
        (
            "GET / HTTP/1.1\r\nHost: evil.com\r\n\r\n",
            403,
            "Host header 'evil.com' not allowed",
            "Malicious Host header"
        ),
        (
            "GET / HTTP/1.1\r\nHost: localhost:9999\r\n\r\n",
            403,
            "Host header port 9999 doesn't match server port 8080",
            "Wrong port in Host header"
        ),
    ]
    
    results = []
    
    for request, expected_status, expected_reason, description in test_cases:
        print(f"Testing: {description}")
        
        # Send request
        status_code, response = send_http_request(request)
        
        # Check if we got expected status
        if status_code == expected_status:
            print(f"  ✓ Got expected status {status_code}")
        else:
            print(f"  ✗ Expected status {expected_status}, got {status_code}")
            results.append(False)
            continue
        
        # Wait a moment for logging
        time.sleep(0.1)
        
        # Check security log
        log_entries = check_security_log()
        if log_entries:
            # Find the most recent entry
            recent_entry = log_entries[-1].strip()
            if expected_reason in recent_entry:
                print(f"  ✓ Security violation logged: {recent_entry}")
                results.append(True)
            else:
                print(f"  ✗ Expected reason '{expected_reason}' not found in log entry")
                print(f"    Log entry: {recent_entry}")
                results.append(False)
        else:
            print(f"  ✗ No security log entries found")
            results.append(False)
        
        print()
    
    return results

def check_server_running():
    """Check if server is running."""
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2.0)
        test_sock.connect(('127.0.0.1', 8080))
        test_sock.close()
        return True
    except Exception:
        return False

def main():
    """Main test function."""
    print("=" * 70)
    print("SECURITY VIOLATION LOGGING INTEGRATION TEST")
    print("=" * 70)
    print("This test verifies that security violations are properly logged")
    print("to both the security.log file and stdout.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run the tests
    results = test_security_logging()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 70)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ ALL SECURITY LOGGING TESTS PASSED")
        print("Security violations are being properly logged.")
        
        # Show final security log
        if os.path.exists("security.log"):
            print("\nSecurity log contents:")
            print("-" * 40)
            with open("security.log", 'r') as f:
                print(f.read())
    else:
        print("✗ SOME SECURITY LOGGING TESTS FAILED")
        print("Security violations may not be properly logged.")
    
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
