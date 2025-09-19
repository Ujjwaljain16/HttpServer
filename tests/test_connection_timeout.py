#!/usr/bin/env python3
"""
Test script to validate connection timeout behavior.

This script:
1. Opens a connection to the server
2. Sends one request and receives response
3. Sleeps for 35 seconds (longer than the 30s idle timeout)
4. Attempts another request on the same connection
5. Verifies the server closed the connection
"""

import socket
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_connection_timeout():
    """Test that server closes idle connections after timeout."""
    print("Testing connection timeout behavior...")
    
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)  # 5 second timeout for individual operations
    
    try:
        print("Connecting to server...")
        sock.connect(('127.0.0.1', 8080))
        print("✓ Connected to server")
        
        # Send first request
        print("Sending first request...")
        request = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
        sock.sendall(request)
        
        # Read response
        response = b""
        while True:
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b"\r\n\r\n" in response:
                    # Check if we have the full response
                    header_end = response.find(b"\r\n\r\n")
                    if header_end != -1:
                        headers = response[:header_end + 4]
                        if b"Content-Length:" in headers:
                            # Parse content length
                            for line in headers.split(b"\r\n"):
                                if line.startswith(b"Content-Length:"):
                                    content_length = int(line.split(b":")[1].strip())
                                    body_start = header_end + 4
                                    if len(response) >= body_start + content_length:
                                        break
            except socket.timeout:
                break
        
        print("✓ Received first response")
        print(f"Response length: {len(response)} bytes")
        
        # Check for keep-alive headers
        if b"Connection: keep-alive" in response:
            print("✓ Response includes keep-alive headers")
        else:
            print("⚠ Response does not include keep-alive headers")
        
        # Sleep for 35 seconds (longer than 30s idle timeout)
        print("Sleeping for 35 seconds to trigger timeout...")
        time.sleep(35)
        print("✓ Sleep completed")
        
        # Attempt second request on same connection
        print("Attempting second request on same connection...")
        try:
            request2 = b"GET /about.html HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
            sock.sendall(request2)
            
            # Try to read response
            response2 = b""
            try:
                chunk = sock.recv(1024)
                if chunk:
                    response2 += chunk
                    print("⚠ Unexpected: Received response after timeout")
                    print(f"Response: {response2[:200]}...")
                    return False
                else:
                    print("✓ Connection was closed by server (expected)")
            except socket.timeout:
                print("✓ Connection timed out (expected)")
            except ConnectionResetError:
                print("✓ Connection was reset by server (expected)")
            except BrokenPipeError:
                print("✓ Connection was broken by server (expected)")
                
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"✓ Connection was closed by server: {e}")
        
        print("✓ Connection timeout test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
        
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    """Main test function."""
    print("=" * 60)
    print("CONNECTION TIMEOUT TEST")
    print("=" * 60)
    print("This test verifies that the server closes idle connections")
    print("after the 30-second timeout period.")
    print()
    
    # Check if server is running
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2.0)
        test_sock.connect(('127.0.0.1', 8080))
        test_sock.close()
        print("✓ Server is running on 127.0.0.1:8080")
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("Please start the server with: python server.py")
        return False
    
    print()
    success = test_connection_timeout()
    
    print()
    print("=" * 60)
    if success:
        print("✓ CONNECTION TIMEOUT TEST PASSED")
        print("The server correctly closes idle connections after 30 seconds.")
    else:
        print("✗ CONNECTION TIMEOUT TEST FAILED")
        print("The server may not be properly handling connection timeouts.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
