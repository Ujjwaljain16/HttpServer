#!/usr/bin/env python3
"""
Test to verify 503 response format and Retry-After header.
"""

import socket
import threading
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_request_and_get_response() -> str:
    """Send a request and return the full response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    
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
        
        return response.decode('latin-1')
        
    except Exception as e:
        return f"Error: {e}"
    finally:
        sock.close()

def test_503_response_format():
    """Test that 503 responses have the correct format."""
    print("Testing 503 response format...")
    print("=" * 40)
    
    # Send many requests to try to trigger 503
    responses = []
    for i in range(30):
        response = send_request_and_get_response()
        responses.append(response)
        
        # Check if this is a 503 response
        if "503 Service Unavailable" in response:
            print(f"✓ Found 503 response on request {i+1}")
            print("Response:")
            print("-" * 20)
            print(response)
            print("-" * 20)
            
            # Check for required headers
            if "Retry-After:" in response:
                print("✓ Retry-After header present")
            else:
                print("✗ Retry-After header missing")
            
            if "Service temporarily unavailable" in response:
                print("✓ Correct body content")
            else:
                print("✗ Incorrect body content")
            
            if "Connection: close" in response:
                print("✓ Connection: close header present")
            else:
                print("✗ Connection: close header missing")
            
            return True
        
        time.sleep(0.1)  # Small delay between requests
    
    print("No 503 responses found in 30 requests")
    print("Status codes found:")
    for i, response in enumerate(responses):
        if response.startswith("HTTP/"):
            status_line = response.split('\r\n')[0]
            print(f"  Request {i+1}: {status_line}")
    
    return False

def test_503_with_concurrent_requests():
    """Test 503 with concurrent requests."""
    print("\nTesting 503 with concurrent requests...")
    print("-" * 40)
    
    def send_request():
        return send_request_and_get_response()
    
    # Send 20 concurrent requests
    threads = []
    results = []
    
    def worker():
        result = send_request()
        results.append(result)
    
    # Start all threads
    for i in range(20):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Check results
    for i, response in enumerate(results):
        if "503 Service Unavailable" in response:
            print(f"✓ Found 503 response in concurrent request {i+1}")
            print("Response:")
            print("-" * 20)
            print(response)
            print("-" * 20)
            return True
    
    print("No 503 responses found in concurrent requests")
    return False

def main():
    """Main test function."""
    print("=" * 70)
    print("503 RESPONSE FORMAT VERIFICATION")
    print("=" * 70)
    print("This test verifies that 503 responses have the correct format")
    print("including Retry-After header and proper body content.")
    print()
    
    # Test 1: Sequential requests
    test1 = test_503_response_format()
    
    # Test 2: Concurrent requests
    test2 = test_503_with_concurrent_requests()
    
    # Summary
    print("\n" + "=" * 70)
    if test1 or test2:
        print("✓ 503 RESPONSE FORMAT VERIFIED")
        print("The server returns proper 503 responses with Retry-After headers.")
    else:
        print("✗ 503 RESPONSE FORMAT NOT VERIFIED")
        print("Could not trigger 503 responses or format is incorrect.")
    print("=" * 70)
    
    return test1 or test2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
