#!/bin/bash
# HTTP Server Demo Script
# Run this to demonstrate the server's capabilities

echo "🚀 Multi-threaded HTTP Server Demo"
echo "=================================="
echo

# Check if server is running
echo "1. Checking server status..."
if curl -s --connect-timeout 2 http://127.0.0.1:8080/ > /dev/null 2>&1; then
    echo "✅ Server is running on http://127.0.0.1:8080"
else
    echo "❌ Server is not running. Please start it first:"
    echo "   python server.py 8080 127.0.0.1 4"
    exit 1
fi

echo
echo "2. Testing basic functionality..."

# Test homepage
echo "📄 Homepage (GET /):"
curl -s http://127.0.0.1:8080/ | head -5
echo

# Test file download
echo "📁 File download (GET /logo.png):"
curl -s -I http://127.0.0.1:8080/logo.png | grep -E "(HTTP|Content-Type|Content-Length)"
echo

# Test JSON upload
echo "📤 JSON upload (POST /upload):"
curl -s -X POST -H "Content-Type: application/json" -d '{"demo": "data", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' http://127.0.0.1:8080/upload
echo
echo

echo "3. Testing security features..."

# Test path traversal protection
echo "🔒 Path traversal protection (GET /../etc/passwd):"
curl -s -w "Status: %{http_code}\n" http://127.0.0.1:8080/../etc/passwd
echo

# Test Host header validation
echo "🔒 Host header validation (Host: evil.com):"
curl -s -w "Status: %{http_code}\n" -H "Host: evil.com" http://127.0.0.1:8080/
echo

# Test missing Host header
echo "🔒 Missing Host header:"
curl -s -w "Status: %{http_code}\n" -H "Host:" http://127.0.0.1:8080/
echo

echo "4. Running comprehensive integration tests..."
echo "🧪 Integration Test Suite:"
python tests/integration_test.py

echo
echo "🎉 Demo complete! Check the server logs for detailed information."
echo "   The server supports persistent connections, thread pooling,"
echo "   security validation, and comprehensive error handling."
