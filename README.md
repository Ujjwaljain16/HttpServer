# 🚀 Multi-threaded HTTP Server

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-100%25%20passing-brightgreen.svg)](#testing)
[![Security](https://img.shields.io/badge/Security-Enterprise%20Grade-red.svg)](#security-features)
[![Performance](https://img.shields.io/badge/Performance-500%2B%20req%2Fs-orange.svg)](#performance)

**A production-ready, multi-threaded HTTP/1.1 server built from scratch**  
*Demonstrating advanced Python networking, concurrent programming, security implementation*


</div>

---

## 🎯 Project Overview

This project showcases a complete HTTP server implementation. Built entirely from scratch using Python's standard library, it demonstrates :

- **System Programming** - Low-level socket programming and network protocols
- **Concurrent Programming** - Multi-threading with bounded thread pools
- **Security Engineering** - Comprehensive security measures and attack prevention
- **Production Operations** - Monitoring, logging, and deployment automation
- **Modern DevOps** - Production deployment and monitoring practices

## 🎯 Live Demo

**See it in action!** Run the comprehensive test suite to showcase all features:

```bash
# Start the server
python server.py 8080 127.0.0.1 4

# Run the comprehensive test suite
python final_demo_test.py
```

**Demo Output:**
**Screenshots:**
<img width="1729" height="785" alt="Screenshot 2025-09-20 165751" src="https://github.com/user-attachments/assets/4b958797-2b0c-404c-b582-b263341a2084" />
<img width="1668" height="853" alt="Screenshot 2025-09-20 165806" src="https://github.com/user-attachments/assets/4274310c-f9f1-4e0a-b0f5-63701fe36f47" />
<img width="1188" height="882" alt="Screenshot 2025-09-20 165817" src="https://github.com/user-attachments/assets/11c23cb2-f796-40fd-9405-b33f74e5f63e" />

## ✨ Key Features

### 🌐 **HTTP/1.1 Compliance**
- ✅ **Persistent Connections** - Keep-alive with 30-second idle timeout
- ✅ **Request Limits** - Maximum 100 requests per connection
- ✅ **Proper Headers** - Connection, Keep-Alive, Content-Type, Content-Length
- ✅ **Status Codes** - 200, 201, 400, 403, 404, 405, 415, 503

### 🔧 **Multi-threading & Performance**
- ✅ **Thread Pool** - Fixed-size worker thread pool with bounded queue
- ✅ **Graceful Degradation** - 503 responses when thread pool is saturated
- ✅ **Connection Management** - Efficient socket handling and cleanup
- ✅ **Resource Optimization** - Bounded queue prevents memory exhaustion
- ✅ **High Throughput** - 500+ requests/second capability

### 🔒 **Enterprise Security**
- ✅ **Path Traversal Protection** - Blocks `../` and percent-encoded attacks
- ✅ **Host Header Validation** - Prevents Host header injection attacks
- ✅ **Input Sanitization** - JSON validation and content-type checking
- ✅ **Security Logging** - Comprehensive audit trail for security violations
- ✅ **Rate Limiting** - Per-IP rate limiting with burst protection
- ✅ **Request Size Limiting** - DoS protection with configurable limits
- ✅ **CORS Support** - Cross-origin resource sharing for web applications
- ✅ **Security Dashboard** - Real-time attack monitoring and visualization

### 📊 **Advanced Monitoring & Observability**
- ✅ **Thread Tracking** - Real-time thread status monitoring
- ✅ **JSON Logging** - Structured logging for analysis
- ✅ **Security Audit** - Detailed security violation logging
- ✅ **Performance Metrics** - Request timing and thread utilization
- ✅ **Response Time Tracking** - Per-request performance monitoring
- ✅ **Memory Monitoring** - System resource usage tracking
- ✅ **Prometheus Metrics** - `/metrics` endpoint for monitoring systems
- ✅ **Connection Pooling** - Efficient resource management

### 🧪 **Comprehensive Testing**
- ✅ **Unit Tests** - 28+ tests with 100% pass rate
- ✅ **Integration Tests** - Complete end-to-end testing
- ✅ **Load Testing** - Thread pool saturation and 503 behavior
- ✅ **Security Testing** - Path traversal and Host header validation
- ✅ **Performance Testing** - Concurrent request handling

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- No external dependencies (uses only standard library)

### Installation
```bash
# Clone the repository
git clone https://github.com/ujjwaljain16/multi-threaded-http-server.git


# Install dependencies (optional - for monitoring features)
pip install -r requirements.txt
```

### Running the Server
```bash
# Basic usage (default: 127.0.0.1:8080, 10 threads)
python server.py

# Custom configuration
python server.py 9090 0.0.0.0 20
```

### Example Usage
```bash
# Get performance metrics
curl http://127.0.0.1:8080/metrics

# View security dashboard
curl http://127.0.0.1:8080/security-dashboard

# Test CORS
curl -H "Origin: http://localhost:3000" http://127.0.0.1:8080/

# Test advanced features
python test_advanced_features.py
```

## 📖 Documentation

This project includes comprehensive documentation:

- **[Technical Documentation](TECHNICAL_DOCUMENTATION.md)** - Implementation details, architecture, and technical specifications
- **[Theoretical Documentation](THEORETICAL_DOCUMENTATION.md)** - Concepts, principles, and theory behind the implementation


## 📁 Project Structure

```
├── server.py                      # Main server entry point
├── server_lib/                    # Core server modules
│   ├── __init__.py               # Package initialization
│   ├── http_parser.py            # HTTP request parsing
│   ├── threadpool.py             # Thread pool implementation
│   ├── security.py               # Security and validation
│   ├── response.py               # HTTP response building
│   ├── logger.py                 # Enhanced logging system
│   ├── metrics.py                # Performance metrics collection
│   ├── metrics_endpoint.py       # Metrics API endpoint
│   ├── rate_limiter.py           # Rate limiting implementation
│   ├── request_limiter.py        # Request size limiting
│   ├── cors.py                   # CORS support
│   ├── security_dashboard.py     # Security monitoring dashboard
│   ├── connection_pool.py        # Connection pooling
│   └── utils.py                  # Utility functions
├── resources/                     # Static files and samples
│   ├── index.html                # Professional homepage
│   ├── about.html                # Technical documentation
│   ├── contact.html              # Interactive API testing
│   ├── logo.png                  # Logo image
│   ├── photo.jpg, photo2.jpg     # Sample images
│   ├── big.png                   # Large image for testing
│   ├── readme.txt                # Text file for testing
│   ├── sample.txt                # Sample text file
│   ├── sample_data.json          # Sample JSON data
│   ├── simple_test.json          # Test JSON file
│   ├── test_payload.json         # Test payload
│   └── uploads/                  # POST upload directory
│       └── upload_*.json         # Uploaded files
├── final_demo_test.py            # Comprehensive test suite (28 tests)
├── quick_test.py                 # Quick functionality test
├── requirements.txt              # Python dependencies
├── REQUIREMENTS_CHECKLIST.md     # Requirements verification
├── TECHNICAL_DOCUMENTATION.md    # Technical implementation docs
├── THEORETICAL_DOCUMENTATION.md  # Theoretical concepts docs
├── security.log                  # Security violation logs
└── README.md                     # This file
```

## 🌐 API Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/` | Homepage with features showcase | 200 OK |
| `GET` | `/about.html` | Technical documentation | 200 OK |
| `GET` | `/contact.html` | Interactive API testing | 200 OK |
| `GET` | `/readme.txt` | Text file download | 200 OK |
| `GET` | `/sample.txt` | Sample text file | 200 OK |
| `GET` | `/logo.png` | Logo image file | 200 OK |
| `GET` | `/photo.jpg` | Sample image | 200 OK |
| `GET` | `/photo2.jpg` | Sample image | 200 OK |
| `GET` | `/big.png` | Large image for testing | 200 OK |
| `GET` | `/sample_data.json` | Sample JSON data | 200 OK |
| `GET` | `/simple_test.json` | Test JSON file | 200 OK |
| `GET` | `/test_payload.json` | Test payload | 200 OK |
| `GET` | `/metrics` | Performance metrics | 200 OK |
| `GET` | `/security-dashboard` | Security monitoring | 200 OK |
| `POST` | `/upload` | JSON data upload | 201 Created |

### Example Usage

```bash
# Get homepage
curl http://127.0.0.1:8080/

# Download text file
curl -O http://127.0.0.1:8080/readme.txt

# Download image
curl -O http://127.0.0.1:8080/logo.png

# Get JSON data
curl http://127.0.0.1:8080/sample_data.json

# Upload JSON
curl -X POST -H "Content-Type: application/json" \
     -d '{"test": "data"}' http://127.0.0.1:8080/upload

# Get metrics
curl http://127.0.0.1:8080/metrics

# View security dashboard
curl http://127.0.0.1:8080/security-dashboard

# Test security (should return 403)
curl http://127.0.0.1:8080/../etc/passwd
```

## 🔧 Configuration

### Command Line Arguments
```bash
python server.py [port] [host] [thread_pool_size]
```

- `port`: Server port (default: 8080)
- `host`: Server host (default: 127.0.0.1)
- `thread_pool_size`: Number of worker threads (default: 10

  ---
 
<div align="center">
     
[![GitHub](https://img.shields.io/badge/GitHub-ujjwaljain16-black.svg)](https://github.com/ujjwaljain16)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
</div>
