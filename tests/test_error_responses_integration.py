#!/usr/bin/env python3
"""
Integration test for standardized error responses.

This script tests that the server returns proper error responses
for various error conditions.
"""

import socket
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_http_request(request: str, port: int = 8080) -> tuple[int, str, str]:
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
                # Check if we need to read more for the body
                header_end = response.find(b"\r\n\r\n")
                headers = response[:header_end + 4]
                if b"Content-Length:" in headers:
                    # Parse content length
                    for line in headers.split(b"\r\n"):
                        if line.startswith(b"Content-Length:"):
                            content_length = int(line.split(b":")[1].strip())
                            body_start = header_end + 4
                            if len(response) >= body_start + content_length:
                                break
                    else:
                        continue
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

def test_error_responses():
    """Test various error responses."""
    print("Testing standardized error responses...")
    print("=" * 60)
    
    test_cases = [
        # (request, expected_status, expected_reason, expected_body_contains, description)
        (
            "PUT / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n",
            405,
            "Method Not Allowed",
            "Method not allowed. Allowed methods: GET, POST",
            "405 Method Not Allowed for unsupported method"
        ),
        (
            "DELETE / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n",
            405,
            "Method Not Allowed",
            "Method not allowed. Allowed methods: GET, POST",
            "405 Method Not Allowed for DELETE method"
        ),
        (
            "GET /nonexistent.html HTTP/1.1\r\nHost: localhost:8080\r\n\r\n",
            404,
            "Not Found",
            "Not Found",
            "404 Not Found for missing file"
        ),
        (
            "GET /../etc/passwd HTTP/1.1\r\nHost: localhost:8080\r\n\r\n",
            403,
            "Forbidden",
            "Forbidden",
            "403 Forbidden for path traversal"
        ),
        (
            "GET / HTTP/1.1\r\n\r\n",  # Missing Host header
            400,
            "Bad Request",
            "Missing Host header",
            "400 Bad Request for missing Host header"
        ),
        (
            "GET / HTTP/1.1\r\nHost: evil.com\r\n\r\n",
            403,
            "Forbidden",
            "Host mismatch",
            "403 Forbidden for malicious Host header"
        ),
        (
            "POST /upload HTTP/1.1\r\nHost: localhost:8080\r\nContent-Type: text/plain\r\nContent-Length: 5\r\n\r\nhello",
            415,
            "Unsupported Media Type",
            "Only application/json accepted",
            "415 Unsupported Media Type for non-JSON POST"
        ),
    ]
    
    results = []
    
    for request, expected_status, expected_reason, expected_body, description in test_cases:
        print(f"Testing: {description}")
        request_line = request.split('\r\n')[0]
        print(f"  Request: {request_line}")
        
        status_code, reason, body = send_http_request(request)
        
        # Check status code
        if status_code == expected_status:
            print(f"  ✓ Status code: {status_code}")
        else:
            print(f"  ✗ Expected status {expected_status}, got {status_code}")
            results.append(False)
            continue
        
        # Check reason phrase
        if expected_reason in reason:
            print(f"  ✓ Reason phrase: {reason}")
        else:
            print(f"  ✗ Expected reason '{expected_reason}', got '{reason}'")
            results.append(False)
            continue
        
        # Check body content
        if expected_body in body:
            print(f"  ✓ Body contains expected text")
        else:
            print(f"  ✗ Expected body to contain '{expected_body}', got '{body[:100]}...'")
            results.append(False)
            continue
        
        print(f"  ✓ Test passed")
        results.append(True)
        print()
    
    return results

def test_405_allow_header():
    """Test that 405 responses include the Allow header."""
    print("Testing 405 Method Not Allowed Allow header...")
    print("-" * 40)
    
    request = "PUT / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
    status_code, reason, body = send_http_request(request)
    
    if status_code == 405:
        print("✓ Got 405 status")
        
        # Send raw request to check headers
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        try:
            sock.connect(('127.0.0.1', 8080))
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
            
            response_str = response.decode('latin-1')
            
            if "Allow: GET, POST" in response_str:
                print("✓ Allow header present with correct methods")
                return True
            else:
                print("✗ Allow header missing or incorrect")
                print(f"  Response headers: {response_str[:500]}...")
                return False
                
        except Exception as e:
            print(f"✗ Error testing Allow header: {e}")
            return False
        finally:
            sock.close()
    else:
        print(f"✗ Expected 405, got {status_code}")
        return False

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
    print("STANDARDIZED ERROR RESPONSES INTEGRATION TEST")
    print("=" * 70)
    print("This test verifies that the server returns proper standardized")
    print("error responses for various error conditions.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run the tests
    results = test_error_responses()
    allow_header_test = test_405_allow_header()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 70)
    print(f"RESULTS: {passed}/{total} error response tests passed")
    print(f"Allow header test: {'PASSED' if allow_header_test else 'FAILED'}")
    
    if passed == total and allow_header_test:
        print("✓ ALL ERROR RESPONSE TESTS PASSED")
        print("The server returns proper standardized error responses.")
    else:
        print("✗ SOME ERROR RESPONSE TESTS FAILED")
        print("The server may not be returning proper error responses.")
    
    print("=" * 70)
    
    return passed == total and allow_header_test

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
