#!/usr/bin/env python3
"""
Integration test for Host header validation.

This script tests the Host header validation by sending various HTTP requests
with different Host headers and verifying the server responds correctly.
"""

import socket
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_http_request(host_header: str, port: int = 8080) -> tuple[int, str, str]:
    """Send HTTP request with specific Host header and return response details."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    
    try:
        sock.connect(('127.0.0.1', port))
        
        # Build HTTP request
        request = f"GET / HTTP/1.1\r\nHost: {host_header}\r\n\r\n"
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
        
        # Parse response
        response_str = response.decode('latin-1')
        lines = response_str.split('\r\n')
        status_line = lines[0]
        
        # Extract status code and reason
        parts = status_line.split(' ', 2)
        status_code = int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""
        
        # Extract body
        body_start = response_str.find('\r\n\r\n')
        body = response_str[body_start + 4:] if body_start != -1 else ""
        
        return status_code, reason, body
        
    except Exception as e:
        return 0, f"Error: {e}", ""
    finally:
        sock.close()

def test_host_validation():
    """Test various Host header scenarios."""
    print("Testing Host header validation...")
    print("=" * 60)
    
    test_cases = [
        # (host_header, expected_status, expected_reason, description)
        ("localhost", 200, "OK", "Valid localhost"),
        ("localhost:8080", 200, "OK", "Valid localhost with port"),
        ("127.0.0.1", 200, "OK", "Valid 127.0.0.1"),
        ("127.0.0.1:8080", 200, "OK", "Valid 127.0.0.1 with port"),
        ("", 400, "Bad Request", "Missing Host header"),
        ("evil.com", 403, "Forbidden", "Malicious host"),
        ("evil.com:8080", 403, "Forbidden", "Malicious host with port"),
        ("malicious.com", 403, "Forbidden", "Another malicious host"),
        ("localhost:9000", 403, "Forbidden", "Wrong port"),
        ("127.0.0.1:9000", 403, "Forbidden", "Wrong port on 127.0.0.1"),
    ]
    
    results = []
    
    for host_header, expected_status, expected_reason, description in test_cases:
        print(f"Testing: {description}")
        print(f"  Host: '{host_header}'")
        
        status_code, reason, body = send_http_request(host_header)
        
        success = (status_code == expected_status and 
                  (expected_reason in reason or expected_reason == "OK"))
        
        if success:
            print(f"  ✓ PASS - Status: {status_code}, Reason: {reason}")
        else:
            print(f"  ✗ FAIL - Expected: {expected_status} {expected_reason}, Got: {status_code} {reason}")
            if body:
                print(f"    Body: {body[:100]}...")
        
        results.append(success)
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
    print("HOST HEADER VALIDATION INTEGRATION TEST")
    print("=" * 70)
    print("This test verifies that the server properly validates Host headers")
    print("and rejects malicious or invalid Host header values.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run the tests
    results = test_host_validation()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 70)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ ALL HOST VALIDATION TESTS PASSED")
        print("The server correctly validates Host headers and rejects malicious requests.")
    else:
        print("✗ SOME HOST VALIDATION TESTS FAILED")
        print("The server may not be properly validating Host headers.")
    
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
