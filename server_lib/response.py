"""HTTP response helpers."""

from __future__ import annotations

from email.utils import formatdate
from typing import Dict, Iterable, Tuple

SERVER_HEADER = "SimpleThreadedServer/0.1"


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


def make_error_response(code: int, reason: str, body_text: str, close: bool = True) -> bytes:
    body = body_text.encode("utf-8")
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if close:
        headers["Connection"] = "close"
    return build_response(code, reason, headers, body)
