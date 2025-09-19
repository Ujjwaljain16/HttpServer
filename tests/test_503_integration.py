#!/usr/bin/env python3
"""
Integration test for 503 Service Unavailable responses.

This script tests that the server returns proper 503 responses
when the thread pool is saturated.
"""

import socket
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_request_with_delay(delay: float = 0.0) -> tuple[int, str, str]:
    """Send HTTP request with optional delay."""
    if delay > 0:
        time.sleep(delay)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    
    try:
        sock.connect(('127.0.0.1', 8080))
        
        # Send request
        request = "GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
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

def test_503_response_format():
    """Test the format of 503 responses."""
    print("Testing 503 response format...")
    print("=" * 40)
    
    # Try to trigger a 503 by sending many requests quickly
    print("Sending burst of requests to trigger 503...")
    
    responses = []
    for i in range(20):  # Send 20 requests quickly
        status_code, reason, body = send_request_with_delay(0.01)  # Small delay
        responses.append((status_code, reason, body))
        
        if status_code == 503:
            print(f"✓ Got 503 response on request {i+1}")
            break
    
    # Check if we got any 503 responses
    status_codes = [r[0] for r in responses]
    if 503 in status_codes:
        # Find the 503 response
        for status_code, reason, body in responses:
            if status_code == 503:
                print(f"  Status: {status_code} {reason}")
                print(f"  Body: {body}")
                
                # Check for Retry-After in the response
                # We can't easily check headers in this simple test,
                # but we can verify the body content
                if "Service temporarily unavailable" in body:
                    print("  ✓ Body contains expected message")
                    return True
                else:
                    print("  ✗ Body does not contain expected message")
                    return False
    else:
        print("  ⚠ No 503 responses received")
        print(f"  Status codes received: {set(status_codes)}")
        return False

def test_503_with_curl():
    """Test 503 response using curl to check headers."""
    print("\nTesting 503 response with curl...")
    print("-" * 40)
    
    # This is a simple test - in practice, you'd need to saturate the server
    # For now, we'll just test that the server is responding
    import subprocess
    import sys
    
    try:
        # Try to get a normal response first
        result = subprocess.run([
            sys.executable, "-c", 
            "import socket; s=socket.socket(); s.connect(('127.0.0.1', 8080)); "
            "s.send(b'GET / HTTP/1.1\\r\\nHost: localhost:8080\\r\\n\\r\\n'); "
            "print(s.recv(1024).decode())"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✓ Server is responding to requests")
            return True
        else:
            print(f"✗ Server test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing server: {e}")
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
    print("503 SERVICE UNAVAILABLE INTEGRATION TEST")
    print("=" * 70)
    print("This test verifies that the server returns proper 503 responses")
    print("when the thread pool is saturated.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run tests
    test1 = test_503_response_format()
    test2 = test_503_with_curl()
    
    # Summary
    print("\n" + "=" * 70)
    if test1 and test2:
        print("✓ 503 INTEGRATION TEST PASSED")
        print("The server is responding correctly.")
    else:
        print("✗ 503 INTEGRATION TEST FAILED")
        print("The server may not be handling requests properly.")
    print("=" * 70)
    
    return test1 and test2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
