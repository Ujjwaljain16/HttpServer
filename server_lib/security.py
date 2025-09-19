"""Security helpers: safe path resolution and Host header validation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict
from urllib.parse import unquote


class ForbiddenError(Exception):
    pass


class HostMissingError(Exception):
    pass


class HostMismatchError(Exception):
    pass


def _normalize_components(path_str: str) -> list[str]:
    # Normalize slashes and split
    path_str = path_str.replace("\\", "/")
    parts: list[str] = []
    for segment in path_str.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            # Any up-level is forbidden for request paths
            raise ForbiddenError("Path traversal detected")
        parts.append(segment)
    return parts


def safe_resolve_path(request_path: str, resources_dir: Path) -> Path:
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
        raise ForbiddenError("Absolute path not allowed")

    # Normalize components and forbid any '..'
    components = _normalize_components(decoded)

    # Join under resources and resolve
    base = resources_dir.resolve()
    target = (base.joinpath(*components)).resolve()

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
