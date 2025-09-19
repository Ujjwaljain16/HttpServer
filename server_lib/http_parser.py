"""HTTP request parsing utilities.

- receive_http_request: read until CRLF CRLF or raise on size/timeout
- parse_http_request: parse request line and headers into dict

Headers are decoded using latin-1 as per RFC to preserve bytes safely.
"""

from __future__ import annotations

import socket
from typing import Dict, Tuple

CRLF = b"\r\n"
HEADER_TERMINATOR = b"\r\n\r\n"


class BadRequestError(Exception):
    pass


class HeaderTooLargeError(Exception):
    pass


def receive_http_request(
    sock: socket.socket,
    max_header_size: int = 8192,
    header_timeout: float = 2.0,
) -> bytes:
    """Read from socket until header terminator or size exceeded.

    Sets a temporary timeout while reading headers. Returns raw header bytes
    including the trailing CRLF CRLF.
    """
    prev_timeout = sock.gettimeout()
    sock.settimeout(header_timeout)
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
            if HEADER_TERMINATOR in chunk or HEADER_TERMINATOR in b"".join(chunks):
                data = b"".join(chunks)
                idx = data.find(HEADER_TERMINATOR)
                return data[: idx + len(HEADER_TERMINATOR)]
        raise BadRequestError("Connection closed before headers complete")
    except socket.timeout as exc:
        raise BadRequestError("Timed out reading headers") from exc
    finally:
        sock.settimeout(prev_timeout)


def parse_http_request(raw_headers: bytes) -> Tuple[str, str, str, Dict[str, str]]:
    """Parse the start-line and headers into structures.

    Returns (method, path, version, headers_dict) or raises BadRequestError.
    """
    try:
        header_text = raw_headers.decode("latin-1")
        head, _ = header_text.split("\r\n\r\n", 1)
        lines = head.split("\r\n")
        if len(lines) < 1:
            raise BadRequestError("Empty request")
        request_line = lines[0]
        parts = request_line.split(" ")
        if len(parts) != 3:
            raise BadRequestError("Malformed request line")
        method, path, version = parts
        headers: Dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            if ":" not in line:
                raise BadRequestError("Malformed header line")
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        return method, path, version, headers
    except Exception as exc:
        if isinstance(exc, BadRequestError):
            raise
        raise BadRequestError("Failed to parse HTTP request") from exc