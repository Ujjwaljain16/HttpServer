"""HTTP response helpers."""

from __future__ import annotations

from email.utils import formatdate
from typing import Dict, Iterable, Tuple

SERVER_HEADER = "Multi-threaded HTTP Server"


def build_response(
    status_code: int,
    reason: str,
    headers: Dict[str, str],
    body: bytes,
) -> bytes:
    lines = [f"HTTP/1.1 {status_code} {reason}"]
    # Required headers
    base_headers = {
        "Date": formatdate(usegmt=True),
        "Server": SERVER_HEADER,
        "Content-Length": str(len(body)),
    }
    # Merge headers (caller can override if needed)
    merged = {**base_headers, **headers}
    head = "\r\n".join(f"{k}: {v}" for k, v in merged.items())
    return (lines[0] + "\r\n" + head + "\r\n\r\n").encode("latin-1") + body


def make_error_response(
    status_code: int, 
    reason: str, 
    body_text: str, 
    close_connection: bool = False
) -> bytes:
    """Create a standardized HTTP error response.
    
    Args:
        status_code: HTTP status code (e.g., 400, 403, 404, 405, 500)
        reason: HTTP reason phrase (e.g., "Bad Request", "Forbidden", "Not Found")
        body_text: Error message body text
        close_connection: Whether to close the connection (default: False for keep-alive)
        
    Returns:
        Complete HTTP response as bytes
    """
    # Encode body as UTF-8
    body = body_text.encode("utf-8")
    
    # Standard error response headers
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body)),
    }
    
    # Add Connection header based on close_connection parameter
    if close_connection:
        headers["Connection"] = "close"
    else:
        headers["Connection"] = "keep-alive"
        headers["Keep-Alive"] = "timeout=30, max=100"
    
    return build_response(status_code, reason, headers, body)


def make_method_not_allowed_response(allowed_methods: list[str], close_connection: bool = False) -> bytes:
    """Create a 405 Method Not Allowed response with Allow header.
    
    Args:
        allowed_methods: List of allowed HTTP methods (e.g., ["GET", "POST"])
        close_connection: Whether to close the connection (default: False)
        
    Returns:
        Complete HTTP 405 response as bytes
    """
    methods_str = ", ".join(allowed_methods)
    body_text = f"Method not allowed. Allowed methods: {methods_str}"
    
    # Create standard error response
    body = body_text.encode("utf-8")
    
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body)),
        "Allow": methods_str,  # RFC 7231 requires Allow header for 405
    }
    
    # Add Connection header based on close_connection parameter
    if close_connection:
        headers["Connection"] = "close"
    else:
        headers["Connection"] = "keep-alive"
        headers["Keep-Alive"] = "timeout=30, max=100"
    
    return build_response(405, "Method Not Allowed", headers, body)


def make_service_unavailable_response(retry_after: int = 5, close_connection: bool = True) -> bytes:
    """Create a 503 Service Unavailable response with Retry-After header.
    
    Args:
        retry_after: Number of seconds to wait before retrying (default: 5)
        close_connection: Whether to close the connection (default: True)
        
    Returns:
        Complete HTTP 503 response as bytes
    """
    body_text = "Service temporarily unavailable. Please try again later."
    body = body_text.encode("utf-8")
    
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body)),
        "Retry-After": str(retry_after),  # RFC 7231 requires Retry-After for 503
    }
    
    # Add Connection header based on close_connection parameter
    if close_connection:
        headers["Connection"] = "close"
    else:
        headers["Connection"] = "keep-alive"
        headers["Keep-Alive"] = "timeout=30, max=100"
    
    return build_response(503, "Service Unavailable", headers, body)
