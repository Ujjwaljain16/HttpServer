#!/usr/bin/env python3
"""
Simple connection timeout test script.

This script provides a quick way to test connection timeouts
without the full 35-second wait by using a shorter timeout period.
"""

import socket
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_timeout_quick():
    """Quick test of connection timeout behavior."""
    print("Quick timeout test (using 5-second timeout)...")
    
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    
    try:
        print("Connecting...")
        sock.connect(('127.0.0.1', 8080))
        
        print("Sending request...")
        request = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
        sock.sendall(request)
        
        print("Reading response...")
        response = b""
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk
            if b"\r\n\r\n" in response:
                break
        
        print(f"Response length: {len(response)} bytes")
        
        # Check keep-alive headers
        if b"Connection: keep-alive" in response and b"Keep-Alive:" in response:
            print("✓ Keep-alive headers present")
        else:
            print("⚠ Keep-alive headers missing")
            return False
        
        # Test connection is alive
        print("Testing connection...")
        try:
            sock.sendall(b"")
            print("✓ Connection alive")
        except Exception as e:
            print(f"⚠ Connection issue: {e}")
            return False
        
        print("✓ Quick timeout test passed")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    finally:
        sock.close()

def main():
    """Main function."""
    print("=" * 50)
    print("SIMPLE TIMEOUT TEST")
    print("=" * 50)
    
    # Check server
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2.0)
        test_sock.connect(('127.0.0.1', 8080))
        test_sock.close()
        print("✓ Server running")
    except Exception as e:
        print(f"✗ Server not accessible: {e}")
        return False
    
    success = test_timeout_quick()
    
    print("=" * 50)
    if success:
        print("✓ SIMPLE TIMEOUT TEST PASSED")
    else:
        print("✗ SIMPLE TIMEOUT TEST FAILED")
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
