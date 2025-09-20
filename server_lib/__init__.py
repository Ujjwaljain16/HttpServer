"""
Multi-threaded HTTP Server Library

A comprehensive HTTP/1.1 server implementation with advanced features:
- Multi-threading with bounded thread pools
- Security features (path traversal protection, rate limiting)
- Monitoring and metrics collection
- Production-ready logging and error handling
"""

__version__ = "1.0.0"
__author__ = "ujjwaljain16"
__description__ = "Production-ready multi-threaded HTTP server"

# Import key components for easy access
from .http_parser import parse_http_request, receive_http_request
from .threadpool import ThreadPool
from .security import safe_resolve_path, validate_host_header
from .response import build_response, make_error_response
from .logger import setup_logging, get_logger

# Define what gets imported with "from server_lib import *"
__all__ = [
    "parse_http_request",
    "receive_http_request", 
    "ThreadPool",
    "safe_resolve_path",
    "validate_host_header",
    "build_response",
    "make_error_response",
    "setup_logging",
    "get_logger"
]
