#!/usr/bin/env python3
"""
Aggressive load test to trigger 503 Service Unavailable responses.

This script sends a very large number of concurrent requests to definitely
saturate the thread pool and trigger 503 responses.
"""

import socket
import threading
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_request_with_keepalive(request_id: int) -> tuple[int, str, str, str]:
    """Send a request that will keep the connection open to saturate the pool."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30.0)  # Long timeout
    
    try:
        sock.connect(('127.0.0.1', 8080))
        
        # Send request
        request = f"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
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
        
        # Keep connection open for a while to saturate the pool
        time.sleep(2.0)
        
        return request_id, status_code, reason, body
        
    except Exception as e:
        return request_id, 0, f"Error: {e}", ""
    finally:
        sock.close()

def test_503_aggressive():
    """Aggressive test to trigger 503 responses."""
    print("Starting aggressive 503 test...")
    print("Sending many concurrent requests to saturate thread pool...")
    print("=" * 60)
    
    # Send a large number of requests very quickly
    num_requests = 50  # More than the thread pool can handle
    max_workers = 50   # All at once
    
    start_time = time.time()
    
    # Send requests concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all requests
        futures = [executor.submit(send_request_with_keepalive, i) for i in range(num_requests)]
        
        # Collect results as they complete
        results = []
        completed = 0
        
        for future in as_completed(futures, timeout=60):
            try:
                result = future.result()
                results.append(result)
                completed += 1
                
                if completed % 10 == 0:
                    print(f"Completed {completed}/{num_requests} requests...")
                    
            except Exception as e:
                print(f"Request failed: {e}")
                completed += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Analyze results
    status_counts = {}
    error_count = 0
    
    for request_id, status_code, reason, body in results:
        if status_code == 0:
            error_count += 1
        else:
            status_counts[status_code] = status_counts.get(status_code, 0) + 1
    
    # Print results
    print(f"\nAggressive test completed in {duration:.2f} seconds")
    print(f"Total requests: {num_requests}")
    print(f"Completed responses: {len(results) - error_count}")
    print(f"Errors: {error_count}")
    print()
    
    print("Status code distribution:")
    for status_code in sorted(status_counts.keys()):
        count = status_counts[status_code]
        percentage = (count / num_requests) * 100
        print(f"  {status_code}: {count} ({percentage:.1f}%)")
    
    print()
    
    # Check for 503 responses
    if 503 in status_counts:
        count_503 = status_counts[503]
        print(f"✓ 503 Service Unavailable responses: {count_503}")
        print("✓ Thread pool saturation detected and handled correctly")
        return True
    else:
        print("✗ No 503 responses - thread pool may not be saturated")
        print("Try increasing the number of requests or reducing thread pool size")
        return False

def test_503_burst():
    """Test with a burst of requests to trigger 503."""
    print("\nTesting with burst of requests...")
    print("-" * 40)
    
    # Send requests in rapid succession
    results = []
    for i in range(20):  # Send 20 requests quickly
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        try:
            sock.connect(('127.0.0.1', 8080))
            
            # Send request
            request = f"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
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
            
            # Extract status code
            parts = status_line.split(' ', 2)
            status_code = int(parts[1])
            
            results.append(status_code)
            
            if status_code == 503:
                print(f"✓ Got 503 response on request {i+1}")
                print(f"  Response: {response_str[:200]}...")
                return True
                
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
        finally:
            sock.close()
    
    print(f"Status codes received: {set(results)}")
    return 503 in results

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
    print("AGGRESSIVE 503 SERVICE UNAVAILABLE TEST")
    print("=" * 70)
    print("This test aggressively tries to trigger 503 responses")
    print("by saturating the thread pool with concurrent requests.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py 8080 127.0.0.1 2")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run tests
    test1 = test_503_aggressive()
    test2 = test_503_burst()
    
    # Summary
    print("\n" + "=" * 70)
    if test1 or test2:
        print("✓ 503 BEHAVIOR DETECTED")
        print("The server correctly returns 503 responses when saturated.")
    else:
        print("✗ NO 503 BEHAVIOR DETECTED")
        print("The server may not be properly handling thread pool saturation.")
        print("The thread pool may be larger than expected.")
    print("=" * 70)
    
    return test1 or test2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
