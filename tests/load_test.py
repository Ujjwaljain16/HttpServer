#!/usr/bin/env python3
"""Simple load test to verify thread pool queuing and 503 responses."""

import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor


def make_request(host="127.0.0.1", port=8080, delay=0.1):
    """Make a single HTTP request and return response status."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        
        # Send request
        req = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
        s.sendall(req)
        
        # Read response
        resp = s.recv(1024)
        s.close()
        
        # Extract status code
        status_line = resp.split(b"\r\n", 1)[0]
        if b" 200 " in status_line:
            return 200
        elif b" 503 " in status_line:
            return 503
        else:
            return int(status_line.split(b" ")[1])
    except Exception as e:
        print(f"Request failed: {e}")
        return -1


def load_test(concurrent_requests=50, host="127.0.0.1", port=8080):
    """Run load test with concurrent requests."""
    print(f"Starting load test: {concurrent_requests} concurrent requests to {host}:{port}")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(make_request, host, port) for _ in range(concurrent_requests)]
        results = [f.result() for f in futures]
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Count results
    status_200 = results.count(200)
    status_503 = results.count(503)
    errors = results.count(-1)
    
    print(f"\nLoad test results:")
    print(f"  Duration: {duration:.2f}s")
    print(f"  200 OK: {status_200}")
    print(f"  503 Service Unavailable: {status_503}")
    print(f"  Errors: {errors}")
    print(f"  Success rate: {status_200}/{concurrent_requests} ({100*status_200/concurrent_requests:.1f}%)")
    
    return status_200, status_503, errors


if __name__ == "__main__":
    import sys
    concurrent = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    load_test(concurrent)
