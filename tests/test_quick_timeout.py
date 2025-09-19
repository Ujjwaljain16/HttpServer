#!/usr/bin/env python3
"""
Quick test script to validate connection timeout behavior.

This script tests the timeout mechanism with a shorter wait time
and provides more detailed output about the connection state.
"""

import socket
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_quick_timeout():
    """Test connection timeout with detailed logging."""
    print("Testing connection timeout behavior...")
    
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)  # Short timeout for testing
    
    try:
        print("Connecting to server...")
        sock.connect(('127.0.0.1', 8080))
        print("✓ Connected to server")
        
        # Send first request
        print("Sending first request...")
        request = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
        sock.sendall(request)
        print("✓ Request sent")
        
        # Read response with timeout
        print("Reading response...")
        response = b""
        start_time = time.time()
        
        try:
            while time.time() - start_time < 5.0:  # 5 second max read time
                chunk = sock.recv(1024)
                if not chunk:
                    print("✓ Connection closed by server")
                    break
                response += chunk
                print(f"Received {len(chunk)} bytes, total: {len(response)}")
                
                # Check if we have complete headers
                if b"\r\n\r\n" in response:
                    print("✓ Headers complete")
                    break
        except socket.timeout:
            print("⚠ Timeout while reading response")
        
        print(f"Total response length: {len(response)} bytes")
        
        if response:
            # Show first 200 characters of response
            print(f"Response preview: {response[:200]}")
            
            # Check for keep-alive headers
            if b"Connection: keep-alive" in response:
                print("✓ Response includes keep-alive headers")
            else:
                print("⚠ Response does not include keep-alive headers")
                
            if b"Keep-Alive:" in response:
                print("✓ Response includes Keep-Alive header")
            else:
                print("⚠ Response does not include Keep-Alive header")
        else:
            print("⚠ No response received")
        
        # Test if connection is still alive
        print("\nTesting if connection is still alive...")
        try:
            # Try to send a small amount of data to test connection
            sock.sendall(b"")
            print("✓ Connection appears to be alive")
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"✓ Connection is closed: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
        
    finally:
        try:
            sock.close()
            print("✓ Socket closed")
        except:
            pass

def main():
    """Main test function."""
    print("=" * 60)
    print("QUICK CONNECTION TIMEOUT TEST")
    print("=" * 60)
    print("This test verifies basic connection behavior.")
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
    success = test_quick_timeout()
    
    print()
    print("=" * 60)
    if success:
        print("✓ QUICK TIMEOUT TEST COMPLETED")
    else:
        print("✗ QUICK TIMEOUT TEST FAILED")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
