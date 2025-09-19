Simple HTTP Server - README
============================

This is a custom-built HTTP server implemented in Python using only the standard library.

ARCHITECTURE
============

Core Components:
- server.py: Main server entry point
- server_lib/http_parser.py: HTTP request parsing
- server_lib/threadpool.py: Thread pool implementation
- server_lib/security.py: Security and validation
- server_lib/response.py: HTTP response building
- server_lib/logger.py: Enhanced logging system
- server_lib/utils.py: Utility functions

FEATURES
========

HTTP/1.1 Support:
- Persistent connections (keep-alive)
- Proper Connection and Keep-Alive headers
- 30-second idle timeout
- Maximum 100 requests per connection

Request Handling:
- GET requests for static files
- POST requests for JSON uploads
- Proper HTTP status codes (200, 201, 400, 403, 404, 405, 415, 503)
- Content-Type and Content-Disposition headers

Security:
- Path traversal protection
- Host header validation
- Input validation and sanitization
- Security violation logging

Performance:
- Multi-threaded request handling
- Bounded thread pool with queue
- Graceful 503 responses when saturated
- Efficient binary file serving

Logging:
- Timestamped log format
- Thread status tracking
- JSON logging capability
- Security audit trail

USAGE
=====

Start the server:
python server.py [port] [host] [thread_pool_size]

Default values:
- port: 8080
- host: 127.0.0.1
- thread_pool_size: 10

Examples:
python server.py                    # Use defaults
python server.py 9000               # Custom port
python server.py 9000 0.0.0.0 20   # Custom port, host, and thread count

TESTING
=======

Unit Tests:
pytest tests/

Integration Tests:
python tests/verify_all.py
python tests/test_503_load_test.py

Manual Testing:
curl http://127.0.0.1:8080/
curl -O http://127.0.0.1:8080/logo.png
curl -X POST -H "Content-Type: application/json" -d '{"test": "data"}' http://127.0.0.1:8080/upload

RESOURCES
=========

Static Files:
- index.html: Home page
- about.html: About page
- contact.html: Contact and API testing
- sample.txt: This file
- readme.txt: This file
- logo.png: Small PNG image
- big.png: Large PNG image (>1MB)
- photo.jpg: JPEG image
- photo2.jpg: Another JPEG image

API Endpoints:
- GET /: Serves index.html
- GET /{file}: Serves static files
- POST /upload: Accepts JSON uploads

ERROR HANDLING
==============

The server handles various error conditions:
- 400 Bad Request: Malformed requests, missing Host header
- 403 Forbidden: Path traversal attempts, Host header mismatch
- 404 Not Found: File not found
- 405 Method Not Allowed: Unsupported HTTP methods
- 415 Unsupported Media Type: Wrong content type for POST
- 503 Service Unavailable: Thread pool saturated

SECURITY
========

Path Traversal Protection:
- Blocks ../ and percent-encoded traversal attempts
- Validates resolved paths are within resources directory
- Logs security violations

Host Header Validation:
- Requires Host header for all requests
- Validates Host header matches server configuration
- Supports localhost and 127.0.0.1 variations

LOGGING
=======

Log Format:
[YYYY-MM-DD HH:MM:SS] [Thread-Name] LEVEL: message

Log Files:
- Console output: Real-time logging
- server.log: Text log file (if specified)
- server.json: JSON log file (if specified)
- security.log: Security violations

Thread Status:
- Automatic thread registration and tracking
- Status updates (active, idle, busy)
- Periodic thread status logging

PERFORMANCE
===========

Thread Pool:
- Fixed number of worker threads
- Bounded queue for request handling
- Configurable pool size and queue size
- Graceful shutdown with sentinel values

Connection Handling:
- Persistent connections with keep-alive
- Idle timeout management
- Request counting per connection
- Proper connection cleanup

File Serving:
- Efficient binary file reading
- Chunked sending for large files
- Proper Content-Length headers
- Content-Disposition for downloads

This server demonstrates core HTTP server concepts and provides
a solid foundation for understanding web server architecture.
