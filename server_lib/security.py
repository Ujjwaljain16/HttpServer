"""Security helpers: safe path resolution and Host header validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


class ForbiddenError(Exception):
    pass


class HostMissingError(Exception):
    pass


class HostMismatchError(Exception):
    pass


def safe_resolve_path(request_path: str, resources_dir: Path) -> Path:
    """Resolve request_path safely under resources_dir.

    - Reject absolute paths
    - Reject traversal sequences (..), including percent-encoded ones is caller's duty pre-normalization
    - Canonicalize and ensure final path is within resources_dir
    """
    # Normalize leading slash
    rel = request_path.lstrip("/")

    # Block obvious traversal
    if ".." in rel.split("/"):
        raise ForbiddenError("Path traversal detected")

    # Compute canonical absolute path and ensure containment
    base = resources_dir.resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ForbiddenError("Resolved path escapes resources directory") from exc
    return target


def validate_host_header(headers: Dict[str, str], server_host: str, server_port: int) -> bool:
    host = headers.get("host")
    if not host:
        raise HostMissingError("Missing Host header")

    # Accept host:port or host only (default to server_port)
    if ":" in host:
        name, port_str = host.rsplit(":", 1)
        try:
            port_val = int(port_str)
        except ValueError:
            raise HostMismatchError("Invalid Host header port")
    else:
        name, port_val = host, server_port

    # Accept localhost synonyms
    acceptable_names = {server_host, "127.0.0.1", "localhost"}
    if name not in acceptable_names or port_val != server_port:
        raise HostMismatchError("Host header does not match server")
    return True
