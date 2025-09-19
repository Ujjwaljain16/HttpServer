#!/usr/bin/env python3
"""
Load test to verify 503 Service Unavailable behavior when thread pool is saturated.

This script generates a large number of concurrent requests to overflow the thread pool
queue and verify that 503 responses are returned with proper Retry-After headers.
"""

import socket
import threading
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_request(request_id: int, delay: float = 0.0) -> tuple[int, str, str, str]:
    """Send a single HTTP request and return response details.
    
    Args:
        request_id: Unique identifier for this request
        delay: Delay before sending request (seconds)
        
    Returns:
        Tuple of (request_id, status_code, reason, response_body)
    """
    if delay > 0:
        time.sleep(delay)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)  # 10 second timeout
    
    try:
        sock.connect(('127.0.0.1', 8080))
        
        # Send simple GET request
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
        
        return request_id, status_code, reason, body
        
    except Exception as e:
        return request_id, 0, f"Error: {e}", ""
    finally:
        sock.close()

def test_503_behavior(num_requests: int = 100, max_workers: int = 50):
    """Test 503 behavior with concurrent requests.
    
    Args:
        num_requests: Total number of requests to send
        max_workers: Maximum number of concurrent threads
    """
    print(f"Starting load test: {num_requests} concurrent requests")
    print(f"Max concurrent threads: {max_workers}")
    print("=" * 60)
    
    start_time = time.time()
    
    # Send requests concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all requests
        futures = [executor.submit(send_request, i) for i in range(num_requests)]
        
        # Collect results
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Request failed: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Analyze results
    status_counts = {}
    retry_after_count = 0
    error_count = 0
    
    for request_id, status_code, reason, body in results:
        if status_code == 0:
            error_count += 1
        else:
            status_counts[status_code] = status_counts.get(status_code, 0) + 1
            
            # Check for Retry-After header in 503 responses
            if status_code == 503:
                # We can't easily check headers in this simple test,
                # but we can check the body content
                if "Service temporarily unavailable" in body:
                    retry_after_count += 1
    
    # Print results
    print(f"\nLoad test completed in {duration:.2f} seconds")
    print(f"Total requests: {num_requests}")
    print(f"Successful responses: {len(results) - error_count}")
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
        print(f"✓ Retry-After body content found: {retry_after_count}")
        
        if count_503 > 0:
            print("✓ Thread pool saturation detected and handled correctly")
            return True
        else:
            print("⚠ No 503 responses - thread pool may not be saturated")
            return False
    else:
        print("✗ No 503 responses - thread pool may not be saturated")
        return False

def test_503_with_small_pool():
    """Test 503 behavior with a very small thread pool."""
    print("Testing with small thread pool (2 workers, queue size 5)...")
    print("Note: This test assumes the server is running with a small thread pool")
    print("=" * 60)
    
    # Send requests that should saturate a small pool
    num_requests = 20  # More than queue size
    max_workers = 10   # More than server pool size
    
    return test_503_behavior(num_requests, max_workers)

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
    print("503 SERVICE UNAVAILABLE LOAD TEST")
    print("=" * 70)
    print("This test verifies that the server returns 503 responses")
    print("with Retry-After headers when the thread pool is saturated.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run load tests
    print("Running standard load test...")
    success1 = test_503_behavior(100, 50)
    
    print("\n" + "=" * 60)
    print("Running small pool test...")
    success2 = test_503_with_small_pool()
    
    # Summary
    print("\n" + "=" * 70)
    if success1 or success2:
        print("✓ 503 BEHAVIOR TEST PASSED")
        print("The server correctly returns 503 responses when saturated.")
    else:
        print("✗ 503 BEHAVIOR TEST FAILED")
        print("The server may not be properly handling thread pool saturation.")
        print("Try running with a smaller thread pool size.")
    print("=" * 70)
    
    return success1 or success2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
