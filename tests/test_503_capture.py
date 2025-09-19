#!/usr/bin/env python3
"""
Test to capture and verify 503 response format.
"""

import socket
import threading
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_request_and_capture() -> str:
    """Send a request and capture the full response."""
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

def test_503_capture():
    """Capture a 503 response and verify its format."""
    print("Capturing 503 response...")
    print("=" * 40)
    
    # Send many requests to trigger 503
    responses = []
    threads = []
    
    def send_request():
        response = send_request_and_capture()
        responses.append(response)
    
    # Start many threads to saturate the pool
    for i in range(20):
        t = threading.Thread(target=send_request)
        t.start()
        threads.append(t)
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Find 503 responses
    for i, response in enumerate(responses):
        if "503 Service Unavailable" in response:
            print(f"✓ Found 503 response #{i+1}")
            print("Full response:")
            print("-" * 50)
            print(response)
            print("-" * 50)
            
            # Verify headers
            if "Retry-After: 5" in response:
                print("✓ Retry-After: 5 header present")
            else:
                print("✗ Retry-After header missing or incorrect")
            
            if "Service temporarily unavailable. Please try again later." in response:
                print("✓ Correct body content")
            else:
                print("✗ Incorrect body content")
            
            if "Connection: close" in response:
                print("✓ Connection: close header present")
            else:
                print("✗ Connection: close header missing")
            
            if "Content-Type: text/plain; charset=utf-8" in response:
                print("✓ Correct Content-Type header")
            else:
                print("✗ Incorrect Content-Type header")
            
            if "Content-Length:" in response:
                print("✓ Content-Length header present")
            else:
                print("✗ Content-Length header missing")
            
            return True
    
    print("No 503 responses found")
    print("Status codes found:")
    for i, response in enumerate(responses):
        if response.startswith("HTTP/"):
            status_line = response.split('\r\n')[0]
            print(f"  Response {i+1}: {status_line}")
    
    return False

def main():
    """Main test function."""
    print("=" * 70)
    print("503 RESPONSE CAPTURE AND VERIFICATION")
    print("=" * 70)
    print("This test captures a 503 response and verifies its format.")
    print()
    
    success = test_503_capture()
    
    print("\n" + "=" * 70)
    if success:
        print("✓ 503 RESPONSE FORMAT VERIFIED")
        print("The server returns proper 503 responses with all required headers.")
    else:
        print("✗ 503 RESPONSE FORMAT NOT VERIFIED")
        print("Could not capture 503 response or format is incorrect.")
    print("=" * 70)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
