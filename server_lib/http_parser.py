"""
HTTP Request Parser

This module handles the low-level parsing of HTTP requests from raw socket data.
It's responsible for:
- Reading HTTP headers from a socket until we find the end marker
- Parsing the request line (method, path, version)
- Parsing individual headers into a dictionary
- Handling different character encodings properly

The parser follows HTTP/1.1 specification and includes basic security checks.
"""

from __future__ import annotations

import socket
from typing import Dict, Tuple

# HTTP protocol constants
CRLF = b"\r\n"                    # Carriage return + line feed
HEADER_TERMINATOR = b"\r\n\r\n"   # Marks the end of HTTP headers


class BadRequestError(Exception):
    """Raised when an HTTP request is malformed or invalid."""
    pass


class HeaderTooLargeError(Exception):
    """Raised when HTTP headers exceed the maximum allowed size."""
    pass


def receive_http_request(
    sock: socket.socket,
    max_header_size: int = 8192,
    header_timeout: float | None = None,
    timeout: float | None = 2.0,
) -> Tuple[bytes, bytes]:
    """
    Read HTTP request from socket until we find the header terminator.
    
    This function reads data from the socket in chunks until it finds the
    double CRLF that marks the end of HTTP headers. It also enforces a
    maximum header size to prevent memory exhaustion attacks.
    
    Args:
        sock: The socket to read from
        max_header_size: Maximum size of headers in bytes (default: 8KB)
        header_timeout: Deprecated - use 'timeout' instead
        timeout: How long to wait for headers (default: 2 seconds)
        
    Returns:
        Tuple of (header_bytes, body_bytes) - the raw bytes split at the header boundary
        
    Raises:
        HeaderTooLargeError: If headers exceed max_header_size
        BadRequestError: If the request is malformed
    """
    effective_timeout = timeout if timeout is not None else header_timeout
    if effective_timeout is None:
        effective_timeout = 2.0

    prev_timeout = sock.gettimeout()
    sock.settimeout(effective_timeout)
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_header_size:
                raise HeaderTooLargeError("HTTP header section exceeds limit")
            joined = b"".join(chunks)
            idx = joined.find(HEADER_TERMINATOR)
            if idx != -1:
                header = joined[: idx + len(HEADER_TERMINATOR)]
                leftover = joined[idx + len(HEADER_TERMINATOR) :]
                return header, leftover
        raise BadRequestError("Connection closed before headers complete")
    except socket.timeout as exc:
        raise BadRequestError("Timed out reading headers") from exc
    finally:
        sock.settimeout(prev_timeout)


def parse_http_request(raw_headers: bytes) -> Tuple[str, str, str, Dict[str, str]]:
    """Parse the start-line and headers into structures.

    - Returns (method, path, version, headers_dict)
    - Header names are case-insensitive (lower-cased keys)
    - Supports obsolete line folding: continuation lines starting with space or tab
      are appended to the previous header value with a single space
    """
    try:
        header_text = raw_headers.decode("latin-1")
        head, _ = header_text.split("\r\n\r\n", 1)
        raw_lines = head.split("\r\n")
        if not raw_lines:
            raise BadRequestError("Empty request")
        request_line = raw_lines[0]
        parts = request_line.split(" ")
        if len(parts) != 3:
            raise BadRequestError("Malformed request line")
        method, path, version = parts

        # Unfold headers: join lines starting with SP/HTAB to previous header
        unfolded: list[str] = []
        for line in raw_lines[1:]:
            if not line:
                continue
            if line[:1] in (" ", "\t") and unfolded:
                unfolded[-1] = unfolded[-1] + " " + line.lstrip()
            else:
                unfolded.append(line)

        headers: Dict[str, str] = {}
        for line in unfolded:
            if ":" not in line:
                raise BadRequestError("Malformed header line")
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()

        return method, path, version, headers
    except Exception as exc:
        if isinstance(exc, BadRequestError):
            raise
        raise BadRequestError("Failed to parse HTTP request") from exc