#!/usr/bin/env python3
"""
Comprehensive integration test suite for the HTTP server.

This script tests all major functionality:
- GET requests (homepage, file downloads)
- POST requests (JSON upload)
- Security features (path traversal, Host header validation)
- Error handling and status codes
"""

import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class HTTPClient:
    """Simple HTTP client for testing."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
    
    def send_request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, 
                    body: Optional[bytes] = None) -> Tuple[int, Dict[str, str], bytes]:
        """Send HTTP request and return (status_code, headers, body)."""
        if headers is None:
            headers = {}
        
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)  # 10 second timeout
        
        try:
            sock.connect((self.host, self.port))
            
            # Build request
            request_line = f"{method} {path} HTTP/1.1\r\n"
            request_headers = f"Host: {self.host}:{self.port}\r\n"
            for key, value in headers.items():
                request_headers += f"{key}: {value}\r\n"
            
            if body:
                request_headers += f"Content-Length: {len(body)}\r\n"
            
            request_headers += "\r\n"
            
            # Send request
            request = (request_line + request_headers).encode('utf-8')
            if body:
                request += body
            sock.sendall(request)
            
            # Read response
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Check if we have complete headers
                if b"\r\n\r\n" in response:
                    break
            
            # Parse response
            header_end = response.find(b"\r\n\r\n")
            if header_end == -1:
                raise Exception("Invalid HTTP response: no header terminator")
            
            header_text = response[:header_end].decode('utf-8', errors='ignore')
            body_bytes = response[header_end + 4:]
            
            # Parse status line
            lines = header_text.split('\r\n')
            status_line = lines[0]
            status_parts = status_line.split(' ', 2)
            status_code = int(status_parts[1])
            
            # Parse headers
            response_headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    response_headers[key.strip().lower()] = value.strip()
            
            return status_code, response_headers, body_bytes
            
        finally:
            sock.close()

class IntegrationTester:
    """Integration test suite for HTTP server."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.client = HTTPClient(host, port)
        self.host = host
        self.port = port
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        
        self.results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
    
    def test_server_connectivity(self) -> bool:
        """Test basic server connectivity."""
        try:
            status, headers, body = self.client.send_request("GET", "/")
            if status == 200:
                self.log_test("Server Connectivity", True, f"Server responding on {self.host}:{self.port}")
                return True
            else:
                self.log_test("Server Connectivity", False, f"Unexpected status code: {status}")
                return False
        except Exception as e:
            self.log_test("Server Connectivity", False, f"Connection failed: {e}")
            return False
    
    def test_get_homepage(self) -> bool:
        """Test GET / returns 200 and contains <html>."""
        try:
            status, headers, body = self.client.send_request("GET", "/")
            
            if status != 200:
                self.log_test("GET Homepage Status", False, f"Expected 200, got {status}")
                return False
            
            body_text = body.decode('utf-8', errors='ignore')
            if '<html' not in body_text.lower():
                self.log_test("GET Homepage Content", False, f"Response does not contain <html. First 200 chars: {body_text[:200]}")
                return False
            
            # Check Content-Type
            content_type = headers.get('content-type', '')
            if 'text/html' not in content_type:
                self.log_test("GET Homepage Content-Type", False, f"Expected text/html, got {content_type}")
                return False
            
            self.log_test("GET Homepage", True, f"Status: {status}, Content-Type: {content_type}")
            return True
            
        except Exception as e:
            self.log_test("GET Homepage", False, f"Exception: {e}")
            return False
    
    def test_file_download(self) -> bool:
        """Test logo.png download and verify file size."""
        try:
            status, headers, body = self.client.send_request("GET", "/logo.png")
            
            if status != 200:
                self.log_test("File Download Status", False, f"Expected 200, got {status}")
                return False
            
            # Check Content-Type
            content_type = headers.get('content-type', '')
            if 'application/octet-stream' not in content_type:
                self.log_test("File Download Content-Type", False, f"Expected application/octet-stream, got {content_type}")
                return False
            
            # Check Content-Disposition
            disposition = headers.get('content-disposition', '')
            if 'attachment' not in disposition or 'logo.png' not in disposition:
                self.log_test("File Download Disposition", False, f"Expected attachment with filename, got {disposition}")
                return False
            
            # Verify file size matches Content-Length
            content_length = int(headers.get('content-length', '0'))
            actual_size = len(body)
            
            if content_length != actual_size:
                self.log_test("File Download Size", False, f"Content-Length {content_length} != actual size {actual_size}")
                return False
            
            # Check if file exists in resources and compare size
            resources_file = Path("resources/logo.png")
            if not resources_file.exists():
                self.log_test("File Download Source", False, "Source file resources/logo.png does not exist")
                return False
            
            expected_size = resources_file.stat().st_size
            if actual_size != expected_size:
                self.log_test("File Download Content", False, f"Downloaded size {actual_size} != source size {expected_size}")
                return False
            
            self.log_test("File Download", True, f"Size: {actual_size} bytes, Content-Type: {content_type}")
            return True
            
        except Exception as e:
            self.log_test("File Download", False, f"Exception: {e}")
            return False
    
    def test_json_upload(self) -> bool:
        """Test POST /upload and verify 201 response and file creation."""
        try:
            # Prepare test JSON data
            test_data = {
                "test": "integration_test",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "message": "This is a test upload from integration test"
            }
            
            json_body = json.dumps(test_data).encode('utf-8')
            headers = {"Content-Type": "application/json"}
            
            status, response_headers, body = self.client.send_request("POST", "/upload", headers, json_body)
            
            if status != 201:
                self.log_test("JSON Upload Status", False, f"Expected 201, got {status}")
                return False
            
            # Check Content-Type
            content_type = response_headers.get('content-type', '')
            if 'application/json' not in content_type:
                self.log_test("JSON Upload Content-Type", False, f"Expected application/json, got {content_type}")
                return False
            
            # Parse response JSON
            try:
                response_data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.log_test("JSON Upload Response", False, f"Invalid JSON response: {e}")
                return False
            
            # Check response structure
            required_fields = ['status', 'message', 'filepath']
            for field in required_fields:
                if field not in response_data:
                    self.log_test("JSON Upload Response Structure", False, f"Missing field: {field}")
                    return False
            
            if response_data['status'] != 'success':
                self.log_test("JSON Upload Response Status", False, f"Expected 'success', got '{response_data['status']}'")
                return False
            
            # Extract filepath and verify file exists
            filepath = response_data['filepath']
            if not filepath.startswith('/uploads/'):
                self.log_test("JSON Upload Filepath", False, f"Invalid filepath format: {filepath}")
                return False
            
            # Check if file exists in uploads directory
            uploads_file = Path("resources") / filepath.lstrip('/')
            if not uploads_file.exists():
                self.log_test("JSON Upload File Creation", False, f"Uploaded file does not exist: {uploads_file}")
                return False
            
            # Verify file content
            try:
                with open(uploads_file, 'r', encoding='utf-8') as f:
                    uploaded_data = json.load(f)
                
                if uploaded_data != test_data:
                    self.log_test("JSON Upload File Content", False, "Uploaded file content does not match original")
                    return False
                
            except Exception as e:
                self.log_test("JSON Upload File Content", False, f"Error reading uploaded file: {e}")
                return False
            
            self.log_test("JSON Upload", True, f"File created: {filepath}")
            return True
            
        except Exception as e:
            self.log_test("JSON Upload", False, f"Exception: {e}")
            return False
    
    def test_path_traversal(self) -> bool:
        """Test path traversal protection with 403 response."""
        try:
            status, headers, body = self.client.send_request("GET", "/../etc/passwd")
            
            if status != 403:
                self.log_test("Path Traversal Status", False, f"Expected 403, got {status}")
                return False
            
            # Check response body contains "Forbidden"
            body_text = body.decode('utf-8', errors='ignore')
            if 'forbidden' not in body_text.lower():
                self.log_test("Path Traversal Response", False, "Response body should contain 'Forbidden'")
                return False
            
            self.log_test("Path Traversal Protection", True, f"Status: {status}, correctly blocked")
            return True
            
        except Exception as e:
            self.log_test("Path Traversal Protection", False, f"Exception: {e}")
            return False
    
    def test_host_validation(self) -> bool:
        """Test Host header validation with 403 response."""
        try:
            # Create a custom client that sends invalid Host header
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            
            try:
                sock.connect((self.host, self.port))
                
                # Send request with invalid Host header
                request = (
                    "GET / HTTP/1.1\r\n"
                    "Host: evil.com:8080\r\n"
                    "\r\n"
                ).encode('utf-8')
                
                sock.sendall(request)
                
                # Read response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\r\n\r\n" in response:
                        break
                
                # Parse status code
                header_end = response.find(b"\r\n\r\n")
                if header_end == -1:
                    self.log_test("Host Validation", False, "Invalid HTTP response")
                    return False
                
                header_text = response[:header_end].decode('utf-8', errors='ignore')
                status_line = header_text.split('\r\n')[0]
                status_code = int(status_line.split(' ', 2)[1])
                
                if status_code != 403:
                    self.log_test("Host Validation Status", False, f"Expected 403, got {status_code}")
                    return False
                
                # Check response body
                body_bytes = response[header_end + 4:]
                body_text = body_bytes.decode('utf-8', errors='ignore')
                if 'forbidden' not in body_text.lower() and 'host mismatch' not in body_text.lower():
                    self.log_test("Host Validation Response", False, f"Response body should contain 'Forbidden' or 'Host mismatch'. Got: {body_text}")
                    return False
                
                self.log_test("Host Validation", True, f"Status: {status_code}, correctly blocked evil.com")
                return True
                
            finally:
                sock.close()
                
        except Exception as e:
            self.log_test("Host Validation", False, f"Exception: {e}")
            return False
    
    def test_missing_host_header(self) -> bool:
        """Test missing Host header returns 400."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            
            try:
                sock.connect((self.host, self.port))
                
                # Send request without Host header
                request = (
                    "GET / HTTP/1.1\r\n"
                    "\r\n"
                ).encode('utf-8')
                
                sock.sendall(request)
                
                # Read response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\r\n\r\n" in response:
                        break
                
                # Parse status code
                header_end = response.find(b"\r\n\r\n")
                if header_end == -1:
                    self.log_test("Missing Host Header", False, "Invalid HTTP response")
                    return False
                
                header_text = response[:header_end].decode('utf-8', errors='ignore')
                status_line = header_text.split('\r\n')[0]
                status_code = int(status_line.split(' ', 2)[1])
                
                if status_code != 400:
                    self.log_test("Missing Host Header Status", False, f"Expected 400, got {status_code}")
                    return False
                
                self.log_test("Missing Host Header", True, f"Status: {status_code}, correctly rejected")
                return True
                
            finally:
                sock.close()
                
        except Exception as e:
            self.log_test("Missing Host Header", False, f"Exception: {e}")
            return False
    
    def test_unsupported_method(self) -> bool:
        """Test unsupported HTTP method returns 405."""
        try:
            status, headers, body = self.client.send_request("PUT", "/")
            
            if status != 405:
                self.log_test("Unsupported Method Status", False, f"Expected 405, got {status}")
                return False
            
            # Check Allow header
            allow_header = headers.get('allow', '')
            if 'GET' not in allow_header or 'POST' not in allow_header:
                self.log_test("Unsupported Method Allow Header", False, f"Expected Allow header with GET, POST, got: {allow_header}")
                return False
            
            self.log_test("Unsupported Method", True, f"Status: {status}, Allow: {allow_header}")
            return True
            
        except Exception as e:
            self.log_test("Unsupported Method", False, f"Exception: {e}")
            return False
    
    def test_unsupported_content_type(self) -> bool:
        """Test POST with non-JSON content type returns 415."""
        try:
            headers = {"Content-Type": "text/plain"}
            body = b"This is not JSON"
            
            status, response_headers, body = self.client.send_request("POST", "/upload", headers, body)
            
            if status != 415:
                self.log_test("Unsupported Content-Type Status", False, f"Expected 415, got {status}")
                return False
            
            self.log_test("Unsupported Content-Type", True, f"Status: {status}, correctly rejected")
            return True
            
        except Exception as e:
            self.log_test("Unsupported Content-Type", False, f"Exception: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        print("=" * 70)
        print("HTTP SERVER INTEGRATION TEST SUITE")
        print("=" * 70)
        print(f"Testing server at {self.host}:{self.port}")
        print()
        
        # Test server connectivity first
        if not self.test_server_connectivity():
            print("\n❌ Server is not responding. Please start the server first.")
            print("   Run: python server.py 8080 127.0.0.1 2")
            return False
        
        print()
        
        # Run all tests
        tests = [
            self.test_get_homepage,
            self.test_file_download,
            self.test_json_upload,
            self.test_path_traversal,
            self.test_host_validation,
            self.test_missing_host_header,
            self.test_unsupported_method,
            self.test_unsupported_content_type,
        ]
        
        for test in tests:
            test()
            time.sleep(0.1)  # Small delay between tests
        
        # Print summary
        print()
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.tests_passed + self.tests_failed}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed / (self.tests_passed + self.tests_failed)) * 100:.1f}%")
        
        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Server is working correctly.")
            return True
        else:
            print(f"\n⚠️  {self.tests_failed} test(s) failed. Check the output above for details.")
            return False

def main():
    """Main function to run integration tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HTTP Server Integration Test Suite")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    
    args = parser.parse_args()
    
    tester = IntegrationTester(args.host, args.port)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
