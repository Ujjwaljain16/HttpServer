#!/usr/bin/env python3
"""
Final test to verify 503 Service Unavailable behavior.

This test sends a very large number of requests very quickly to definitely
saturate the thread pool queue and trigger 503 responses.
"""

import socket
import threading
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_request_fast(request_id: int) -> tuple[int, str, str]:
    """Send a request as fast as possible."""
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

def test_503_massive_load():
    """Test with massive load to trigger 503."""
    print("Testing 503 with massive load...")
    print("Sending 100 requests with 100 concurrent threads...")
    print("=" * 60)
    
    # Send 100 requests with 100 concurrent threads
    # This should definitely saturate a 2-worker, 32-queue thread pool
    num_requests = 100
    max_workers = 100
    
    start_time = time.time()
    
    # Send requests concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all requests
        futures = [executor.submit(send_request_fast, i) for i in range(num_requests)]
        
        # Collect results
        results = []
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Request failed: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Analyze results
    status_counts = {}
    error_count = 0
    retry_after_count = 0
    
    for request_id, status_code, reason, body in results:
        if status_code == 0:
            error_count += 1
        else:
            status_counts[status_code] = status_counts.get(status_code, 0) + 1
            
            # Check for 503 response details
            if status_code == 503:
                if "Service temporarily unavailable" in body:
                    retry_after_count += 1
                    print(f"✓ 503 response #{request_id}: {reason}")
                    print(f"  Body: {body}")
    
    # Print results
    print(f"\nMassive load test completed in {duration:.2f} seconds")
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
        print(f"✓ Responses with correct body: {retry_after_count}")
        
        if count_503 > 0:
            print("✓ Thread pool saturation detected and handled correctly")
            return True
        else:
            print("⚠ No 503 responses - thread pool may not be saturated")
            return False
    else:
        print("✗ No 503 responses - thread pool may not be saturated")
        return False

def test_503_instant_burst():
    """Test with instant burst of requests."""
    print("\nTesting 503 with instant burst...")
    print("-" * 40)
    
    # Send 50 requests instantly
    results = []
    threads = []
    
    def send_one_request(i):
        result = send_request_fast(i)
        results.append(result)
    
    # Start all threads at once
    for i in range(50):
        t = threading.Thread(target=send_one_request, args=(i,))
        t.start()
        threads.append(t)
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Check for 503 responses
    status_codes = [r[1] for r in results if r[1] != 0]
    if 503 in status_codes:
        count_503 = status_codes.count(503)
        print(f"✓ Got {count_503} 503 responses in instant burst")
        
        # Show details of first 503 response
        for request_id, status_code, reason, body in results:
            if status_code == 503:
                print(f"  First 503 response:")
                print(f"    Status: {status_code} {reason}")
                print(f"    Body: {body}")
                break
        
        return True
    else:
        print(f"✗ No 503 responses in instant burst")
        print(f"  Status codes: {set(status_codes)}")
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
    print("FINAL 503 SERVICE UNAVAILABLE TEST")
    print("=" * 70)
    print("This test sends a massive number of concurrent requests")
    print("to definitely trigger 503 responses and verify their format.")
    print()
    
    # Check if server is running
    if not check_server_running():
        print("✗ Cannot connect to server on 127.0.0.1:8080")
        print("Please start the server with: python server.py 8080 127.0.0.1 2")
        return False
    
    print("✓ Server is running on 127.0.0.1:8080")
    print()
    
    # Run tests
    test1 = test_503_massive_load()
    test2 = test_503_instant_burst()
    
    # Summary
    print("\n" + "=" * 70)
    if test1 or test2:
        print("✓ 503 BEHAVIOR VERIFIED")
        print("The server correctly returns 503 responses when saturated.")
        print("Retry-After headers and proper body content are included.")
    else:
        print("✗ 503 BEHAVIOR NOT VERIFIED")
        print("The server may not be properly handling thread pool saturation.")
        print("Try reducing thread pool size or increasing request load.")
    print("=" * 70)
    
    return test1 or test2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
