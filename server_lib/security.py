"""
Security Module

This module provides security functions to protect the HTTP server from common attacks:
- Path traversal protection (prevents access to files outside the web root)
- Host header validation (prevents Host header injection attacks)
- Input sanitization and validation
- Security event logging

These functions are critical for preventing malicious requests from compromising
the server or accessing sensitive files.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import unquote


class ForbiddenError(Exception):
    """Raised when a request is forbidden due to security restrictions."""
    pass


class HostMissingError(Exception):
    """Raised when the required Host header is missing."""
    pass


class HostMismatchError(Exception):
    """Raised when the Host header doesn't match the server configuration."""
    pass


def log_security_violation(client_addr: str, request_line: str, reason: str, log_file: Optional[str] = None) -> None:
    """Log security violations to both file and stdout.
    
    Args:
        client_addr: Client IP address and port (e.g., "127.0.0.1:12345")
        request_line: HTTP request line (e.g., "GET /../etc/passwd HTTP/1.1")
        reason: Reason for the security violation (e.g., "Path traversal detected")
        log_file: Optional path to security log file (defaults to "security.log")
    """
    if log_file is None:
        log_file = "security.log"
    
    # Get current ISO timestamp
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Format log entry
    log_entry = f"[{timestamp}] SECURITY VIOLATION - {client_addr} - {request_line} - {reason}"
    
    # Write to security log file
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        # If file writing fails, still log to stdout
        print(f"WARNING: Failed to write to security log file {log_file}: {e}", file=sys.stderr)
    
    # Write to stdout
    print(log_entry, file=sys.stdout)
    sys.stdout.flush()


def _normalize_components(path_str: str, client_addr: Optional[str] = None) -> list[str]:
    # Normalize slashes and split
    path_str = path_str.replace("\\", "/")
    parts: list[str] = []
    for segment in path_str.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            # Any up-level is forbidden for request paths
            if client_addr:
                log_security_violation(client_addr, f"GET {path_str} HTTP/1.1", "Path traversal detected")
            raise ForbiddenError("Path traversal detected")
        parts.append(segment)
    return parts


def safe_resolve_path(request_path: str, resources_dir: Path, client_addr: Optional[str] = None) -> Path:
    """Resolve request_path safely under resources_dir.

    - Decode percent-escapes once (blocking %2f, %2e etc. based traversal)
    - Reject absolute paths (after decoding and normalization)
    - Reject traversal sequences ('..')
    - Canonicalize and ensure final path is within resources_dir
    """
    # Strip query string/fragments if accidentally included
    for delim in ("?", "#"):
        if delim in request_path:
            request_path = request_path.split(delim, 1)[0]

    # Decode URL escapes (one pass)
    decoded = unquote(request_path)

    # Quick absolute path checks (posix and windows styles)
    if decoded.startswith(("/", "\\")):
        # Leading slash indicates absolute request; we'll treat as root-relative inside resources
        decoded = decoded.lstrip("/\\")
    # Windows drive letters like C:\ or C:/
    if re.match(r"^[A-Za-z]:[\\/]", decoded):
        if client_addr:
            log_security_violation(client_addr, f"GET {request_path} HTTP/1.1", "Absolute path not allowed")
        raise ForbiddenError("Absolute path not allowed")

    # Normalize components and forbid any '..'
    components = _normalize_components(decoded, client_addr)

    # Join under resources and resolve
    base = resources_dir.resolve()
    target = (base.joinpath(*components)).resolve()

    try:
        target.relative_to(base)
    except ValueError as exc:
        if client_addr:
            log_security_violation(client_addr, f"GET {request_path} HTTP/1.1", "Resolved path escapes resources directory")
        raise ForbiddenError("Resolved path escapes resources directory") from exc

    return target


def validate_host_header(headers: Dict[str, str], server_host: str, server_port: int, client_addr: Optional[str] = None) -> bool:
    """Validate Host header against server configuration.
    
    Args:
        headers: HTTP headers dictionary (case-insensitive keys)
        server_host: Server host address (e.g., '127.0.0.1', '0.0.0.0')
        server_port: Server port number
        
    Returns:
        True if Host header is valid
        
    Raises:
        HostMissingError: If Host header is missing (400 Bad Request)
        HostMismatchError: If Host header doesn't match server (403 Forbidden)
    """
    logger = logging.getLogger("server.security")
    
    host = headers.get("host")
    if not host:
        logger.warning("Request rejected: Missing Host header")
        if client_addr:
            log_security_violation(client_addr, "GET / HTTP/1.1", "Missing Host header")
        raise HostMissingError("Missing Host header")

    # Parse host:port or host only (default to server_port)
    # Handle IPv6 addresses like [::1]:8080 or ::1
    if host.startswith('[') and ']:' in host:
        # IPv6 with port: [::1]:8080
        name, port_str = host.split(']:', 1)
        name = name[1:]  # Remove leading [
        try:
            port_val = int(port_str)
        except ValueError:
            logger.warning(f"Request rejected: Invalid Host header port '{port_str}' in '{host}'")
            if client_addr:
                log_security_violation(client_addr, f"GET / HTTP/1.1", f"Invalid Host header port '{port_str}'")
            raise HostMismatchError("Invalid Host header port")
    elif ":" in host and not host.startswith('[') and not host.startswith('::'):
        # IPv4 with port: localhost:8080 (but not IPv6 like ::1)
        name, port_str = host.rsplit(":", 1)
        try:
            port_val = int(port_str)
        except ValueError:
            logger.warning(f"Request rejected: Invalid Host header port '{port_str}' in '{host}'")
            if client_addr:
                log_security_violation(client_addr, f"GET / HTTP/1.1", f"Invalid Host header port '{port_str}'")
            raise HostMismatchError("Invalid Host header port")
    else:
        # No port specified: localhost or ::1
        name, port_val = host, server_port

    # Determine acceptable host names based on server binding
    if server_host in ("0.0.0.0", "::"):
        # Server bound to all interfaces - accept localhost variants
        acceptable_names = {"127.0.0.1", "localhost", "::1"}
        if server_host == "0.0.0.0":
            # Also accept the actual bound address
            acceptable_names.add("0.0.0.0")
    else:
        # Server bound to specific interface
        acceptable_names = {server_host, "127.0.0.1", "localhost"}
        # If server is bound to 127.0.0.1, also accept 0.0.0.0
        if server_host == "127.0.0.1":
            acceptable_names.add("0.0.0.0")

    # Validate host name and port (case-insensitive)
    name_lower = name.lower()
    acceptable_names_lower = {n.lower() for n in acceptable_names}
    
    if name_lower not in acceptable_names_lower:
        logger.warning(f"Request rejected: Host header '{host}' not in acceptable names {acceptable_names}")
        if client_addr:
            log_security_violation(client_addr, f"GET / HTTP/1.1", f"Host header '{name}' not allowed")
        raise HostMismatchError(f"Host header '{name}' not allowed")
    
    if port_val != server_port:
        logger.warning(f"Request rejected: Host header port {port_val} doesn't match server port {server_port}")
        if client_addr:
            log_security_violation(client_addr, f"GET / HTTP/1.1", f"Host header port {port_val} doesn't match server port {server_port}")
        raise HostMismatchError(f"Host header port {port_val} doesn't match server port {server_port}")
    
    logger.debug(f"Host header validation passed: '{host}'")
    return True
