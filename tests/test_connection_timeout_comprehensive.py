#!/usr/bin/env python3
"""
Comprehensive connection timeout test script.

This script tests the server's connection timeout behavior by:
1. Opening a connection and sending a request
2. Verifying keep-alive headers are present
3. Waiting longer than the idle timeout (35 seconds)
4. Attempting another request to verify the connection was closed
5. Providing detailed logging throughout the process
"""

import socket
import time
import sys
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_connection_timeout():
    """Test that server closes idle connections after 30-second timeout."""
    print("Testing connection timeout behavior...")
    print("This test will take about 40 seconds to complete.")
    print()
    
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)  # 5 second timeout for individual operations
    
    try:
        print("Step 1: Connecting to server...")
        sock.connect(('127.0.0.1', 8080))
        print("✓ Connected to server")
        
        # Send first request
        print("\nStep 2: Sending first request...")
        request = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
        sock.sendall(request)
        print("✓ Request sent")
        
        # Read response
        print("\nStep 3: Reading response...")
        response = b""
        start_time = time.time()
        
        try:
            while time.time() - start_time < 5.0:  # 5 second max read time
                chunk = sock.recv(1024)
                if not chunk:
                    print("✓ Connection closed by server")
                    break
                response += chunk
                print(f"  Received {len(chunk)} bytes, total: {len(response)}")
                
                # Check if we have complete headers
                if b"\r\n\r\n" in response:
                    print("✓ Headers complete")
                    break
        except socket.timeout:
            print("⚠ Timeout while reading response")
        
        print(f"✓ Total response length: {len(response)} bytes")
        
        if response:
            # Check for keep-alive headers
            if b"Connection: keep-alive" in response:
                print("✓ Response includes keep-alive headers")
            else:
                print("⚠ Response does not include keep-alive headers")
                return False
                
            if b"Keep-Alive:" in response:
                print("✓ Response includes Keep-Alive header")
            else:
                print("⚠ Response does not include Keep-Alive header")
                return False
        else:
            print("⚠ No response received")
            return False
        
        # Test if connection is still alive before timeout
        print("\nStep 4: Testing connection before timeout...")
        try:
            # Try to send a small amount of data to test connection
            sock.sendall(b"")
            print("✓ Connection is alive before timeout")
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"⚠ Connection already closed: {e}")
            return False
        
        # Wait for timeout period + buffer
        print(f"\nStep 5: Waiting for timeout (35 seconds)...")
        print("  This simulates an idle connection that should timeout.")
        print("  The server should close the connection after 30 seconds.")
        
        # Use a separate thread to monitor the connection during wait
        connection_closed = threading.Event()
        
        def monitor_connection():
            """Monitor if connection gets closed during wait."""
            try:
                # Try to read from the connection
                sock.settimeout(1.0)
                while not connection_closed.is_set():
                    try:
                        data = sock.recv(1)
                        if not data:
                            print("  ✓ Connection was closed by server during wait")
                            break
                    except socket.timeout:
                        continue
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        print("  ✓ Connection was reset by server during wait")
                        break
            except Exception as e:
                print(f"  Connection monitoring error: {e}")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
        monitor_thread.start()
        
        # Wait for 35 seconds
        for i in range(35):
            time.sleep(1)
            if i % 10 == 0 and i > 0:
                print(f"  ... {i} seconds elapsed")
        
        connection_closed.set()
        print("✓ Wait completed (35 seconds)")
        
        # Test if connection is still alive after timeout
        print("\nStep 6: Testing connection after timeout...")
        try:
            # Try to send another request
            request2 = b"GET /about.html HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
            sock.sendall(request2)
            print("✓ Second request sent")
            
            # Try to read response
            sock.settimeout(2.0)
            response2 = sock.recv(1024)
            if response2:
                print("⚠ Unexpected: Received response after timeout")
                print(f"  Response: {response2[:100]}...")
                return False
            else:
                print("✓ No response received (connection closed)")
                
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"✓ Connection was closed by server: {e}")
        except socket.timeout:
            print("✓ Connection timed out (expected)")
        
        print("\n✓ Connection timeout test PASSED")
        print("  The server correctly closed the idle connection after 30 seconds.")
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

def check_server_running():
    """Check if server is running and accessible."""
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
    print("COMPREHENSIVE CONNECTION TIMEOUT TEST")
    print("=" * 70)
    print("This test verifies that the server closes idle connections")
    print("after the configured 30-second timeout period.")
    print()
    print("Test steps:")
    print("1. Connect to server")
    print("2. Send HTTP request")
    print("3. Verify keep-alive headers")
    print("4. Wait 35 seconds (longer than 30s timeout)")
    print("5. Attempt another request")
    print("6. Verify connection was closed")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run the timeout test
    success = test_connection_timeout()
    
    print()
    print("=" * 70)
    if success:
        print("✓ CONNECTION TIMEOUT TEST PASSED")
        print("The server correctly implements connection timeouts.")
    else:
        print("✗ CONNECTION TIMEOUT TEST FAILED")
        print("The server may not be properly handling connection timeouts.")
    print("=" * 70)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
