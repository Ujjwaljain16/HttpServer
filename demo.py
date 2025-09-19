#!/usr/bin/env python3
"""
HTTP Server Demo Script
Cross-platform demo script for the multi-threaded HTTP server
"""

import requests
import json
import time
import sys

def main():
    print("🚀 Multi-threaded HTTP Server Demo")
    print("=" * 40)
    print()
    
    base_url = "http://127.0.0.1:8080"
    
    # Check if server is running
    print("1. Checking server status...")
    try:
        response = requests.get(base_url, timeout=5)
        print("✅ Server is running on", base_url)
    except requests.exceptions.RequestException as e:
        print("❌ Server is not running. Please start it first:")
        print("   python server.py 8080 127.0.0.1 4")
        return 1
    
    print()
    print("2. Testing basic functionality...")
    
    # Test homepage
    print("📄 Homepage (GET /):")
    response = requests.get(base_url)
    print(f"Status: {response.status_code}")
    print("Content preview:", response.text[:100] + "..." if len(response.text) > 100 else response.text)
    print()
    
    # Test file download
    print("📁 File download (GET /logo.png):")
    response = requests.get(f"{base_url}/logo.png")
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content-Length: {response.headers.get('Content-Length')}")
    print()
    
    # Test JSON upload
    print("📤 JSON upload (POST /upload):")
    data = {
        "demo": "data",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    response = requests.post(f"{base_url}/upload", json=data)
    print(f"Status: {response.status_code}")
    print("Response:", response.text)
    print()
    
    print("3. Testing security features...")
    
    # Test path traversal protection
    print("🔒 Path traversal protection (GET /../etc/passwd):")
    response = requests.get(f"{base_url}/../etc/passwd")
    print(f"Status: {response.status_code} - {'Correctly blocked!' if response.status_code == 403 else 'Unexpected response'}")
    print()
    
    # Test Host header validation
    print("🔒 Host header validation (Host: evil.com):")
    response = requests.get(base_url, headers={"Host": "evil.com:8080"})
    print(f"Status: {response.status_code} - {'Correctly blocked!' if response.status_code == 403 else 'Unexpected response'}")
    print()
    
    # Test missing Host header
    print("🔒 Missing Host header:")
    response = requests.get(base_url, headers={"Host": ""})
    print(f"Status: {response.status_code} - {'Correctly rejected!' if response.status_code == 400 else 'Unexpected response'}")
    print()
    
    print("4. Running comprehensive integration tests...")
    print("🧪 Integration Test Suite:")
    
    # Run integration tests
    import subprocess
    try:
        result = subprocess.run([sys.executable, "tests/integration_test.py"], 
                              capture_output=True, text=True, timeout=30)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except subprocess.TimeoutExpired:
        print("Integration tests timed out")
    except Exception as e:
        print(f"Error running integration tests: {e}")
    
    print()
    print("🎉 Demo complete! Check the server logs for detailed information.")
    print("   The server supports persistent connections, thread pooling,")
    print("   security validation, and comprehensive error handling.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
