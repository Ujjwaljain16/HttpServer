#!/bin/bash
# HTTP Server Integration Test Script
# Tests all major functionality of the HTTP server

set -e  # Exit on any error

HOST="127.0.0.1"
PORT="8080"
BASE_URL="http://${HOST}:${PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test results
print_test() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC} $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC} $test_name"
        if [ -n "$message" ]; then
            echo -e "    $message"
        fi
        ((TESTS_FAILED++))
    fi
}

# Function to check if server is running
check_server() {
    echo "Checking server connectivity..."
    if curl -s --connect-timeout 5 "$BASE_URL/" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is running on $BASE_URL${NC}"
        return 0
    else
        echo -e "${RED}❌ Server is not responding on $BASE_URL${NC}"
        echo "Please start the server first:"
        echo "  python server.py $PORT $HOST 2"
        return 1
    fi
}

# Test 1: GET / returns 200 and contains <html>
test_get_homepage() {
    echo "Testing GET / homepage..."
    
    local response=$(curl -s -w "%{http_code}" "$BASE_URL/")
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$status_code" = "200" ]; then
        if echo "$body" | grep -qi "<html>"; then
            print_test "GET Homepage" "PASS" "Status: $status_code, contains <html>"
        else
            print_test "GET Homepage" "FAIL" "Status: $status_code, but missing <html>"
        fi
    else
        print_test "GET Homepage" "FAIL" "Expected 200, got $status_code"
    fi
}

# Test 2: Download logo.png and verify file size
test_file_download() {
    echo "Testing file download..."
    
    # Download the file
    curl -s -o /tmp/logo_downloaded.png "$BASE_URL/logo.png"
    local status_code=$?
    
    if [ $status_code -eq 0 ]; then
        # Check if file exists and get size
        if [ -f "/tmp/logo_downloaded.png" ]; then
            local downloaded_size=$(stat -c%s "/tmp/logo_downloaded.png" 2>/dev/null || stat -f%z "/tmp/logo_downloaded.png" 2>/dev/null)
            local original_size=$(stat -c%s "resources/logo.png" 2>/dev/null || stat -f%z "resources/logo.png" 2>/dev/null)
            
            if [ "$downloaded_size" = "$original_size" ]; then
                print_test "File Download" "PASS" "Size: $downloaded_size bytes"
            else
                print_test "File Download" "FAIL" "Size mismatch: downloaded $downloaded_size, original $original_size"
            fi
        else
            print_test "File Download" "FAIL" "File was not downloaded"
        fi
    else
        print_test "File Download" "FAIL" "Download failed with status $status_code"
    fi
    
    # Cleanup
    rm -f /tmp/logo_downloaded.png
}

# Test 3: POST JSON to /upload and verify 201 and file creation
test_json_upload() {
    echo "Testing JSON upload..."
    
    # Create test JSON file
    cat > /tmp/test_upload.json << EOF
{
    "test": "integration_test",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "message": "This is a test upload from integration test"
}
EOF
    
    # Send POST request
    local response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d @/tmp/test_upload.json \
        "$BASE_URL/upload")
    
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$status_code" = "201" ]; then
        # Parse JSON response to get filepath
        local filepath=$(echo "$body" | grep -o '"filepath":"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$filepath" ]; then
            # Check if file exists
            local full_path="resources$filepath"
            if [ -f "$full_path" ]; then
                print_test "JSON Upload" "PASS" "File created: $filepath"
            else
                print_test "JSON Upload" "FAIL" "File not found: $full_path"
            fi
        else
            print_test "JSON Upload" "FAIL" "No filepath in response"
        fi
    else
        print_test "JSON Upload" "FAIL" "Expected 201, got $status_code"
    fi
    
    # Cleanup
    rm -f /tmp/test_upload.json
}

# Test 4: Path traversal protection
test_path_traversal() {
    echo "Testing path traversal protection..."
    
    local response=$(curl -s -w "%{http_code}" "$BASE_URL/../etc/passwd")
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$status_code" = "403" ]; then
        if echo "$body" | grep -qi "forbidden"; then
            print_test "Path Traversal Protection" "PASS" "Status: $status_code, correctly blocked"
        else
            print_test "Path Traversal Protection" "FAIL" "Status: $status_code, but missing 'Forbidden' in body"
        fi
    else
        print_test "Path Traversal Protection" "FAIL" "Expected 403, got $status_code"
    fi
}

# Test 5: Host header validation
test_host_validation() {
    echo "Testing Host header validation..."
    
    local response=$(curl -s -w "%{http_code}" -H "Host: evil.com:8080" "$BASE_URL/")
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$status_code" = "403" ]; then
        if echo "$body" | grep -qi "forbidden"; then
            print_test "Host Validation" "PASS" "Status: $status_code, correctly blocked evil.com"
        else
            print_test "Host Validation" "FAIL" "Status: $status_code, but missing 'Forbidden' in body"
        fi
    else
        print_test "Host Validation" "FAIL" "Expected 403, got $status_code"
    fi
}

# Test 6: Missing Host header
test_missing_host() {
    echo "Testing missing Host header..."
    
    # Use curl with custom headers to omit Host header
    local response=$(curl -s -w "%{http_code}" -H "Host:" "$BASE_URL/")
    local status_code="${response: -3}"
    
    if [ "$status_code" = "400" ]; then
        print_test "Missing Host Header" "PASS" "Status: $status_code, correctly rejected"
    else
        print_test "Missing Host Header" "FAIL" "Expected 400, got $status_code"
    fi
}

# Test 7: Unsupported HTTP method
test_unsupported_method() {
    echo "Testing unsupported HTTP method..."
    
    local response=$(curl -s -w "%{http_code}" -X PUT "$BASE_URL/")
    local status_code="${response: -3}"
    
    if [ "$status_code" = "405" ]; then
        print_test "Unsupported Method" "PASS" "Status: $status_code, correctly rejected PUT"
    else
        print_test "Unsupported Method" "FAIL" "Expected 405, got $status_code"
    fi
}

# Test 8: Unsupported content type
test_unsupported_content_type() {
    echo "Testing unsupported content type..."
    
    local response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: text/plain" \
        -d "This is not JSON" \
        "$BASE_URL/upload")
    
    local status_code="${response: -3}"
    
    if [ "$status_code" = "415" ]; then
        print_test "Unsupported Content-Type" "PASS" "Status: $status_code, correctly rejected"
    else
        print_test "Unsupported Content-Type" "FAIL" "Expected 415, got $status_code"
    fi
}

# Main test execution
main() {
    echo "================================================================"
    echo "HTTP SERVER INTEGRATION TEST SUITE"
    echo "================================================================"
    echo "Testing server at $BASE_URL"
    echo
    
    # Check if server is running
    if ! check_server; then
        exit 1
    fi
    
    echo
    
    # Run all tests
    test_get_homepage
    test_file_download
    test_json_upload
    test_path_traversal
    test_host_validation
    test_missing_host
    test_unsupported_method
    test_unsupported_content_type
    
    # Print summary
    echo
    echo "================================================================"
    echo "TEST SUMMARY"
    echo "================================================================"
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    local success_rate=$((TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED)))
    echo "Success Rate: $success_rate%"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo
        echo -e "${GREEN}🎉 ALL TESTS PASSED! Server is working correctly.${NC}"
        exit 0
    else
        echo
        echo -e "${YELLOW}⚠️  $TESTS_FAILED test(s) failed. Check the output above for details.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
