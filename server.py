"""Entry point for the multi-threaded HTTP server.

Parses CLI arguments, prepares the environment, starts a TCP listener, and
accepts connections, handing them to a bounded thread pool for handling.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import socket
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Tuple

from server_lib.http_parser import (
    receive_http_request,
    parse_http_request,
    BadRequestError,
    HeaderTooLargeError,
)
from server_lib.response import build_response, make_error_response
from server_lib.security import (
    safe_resolve_path,
    validate_host_header,
    ForbiddenError,
    HostMissingError,
    HostMismatchError,
)
from server_lib.threadpool import ThreadPool


_shutdown_event = threading.Event()


def _handle_sigint(signum, frame):
    logging.getLogger("server").info("SIGINT received; initiating shutdown")
    _shutdown_event.set()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="server.py",
        description=(
            "Multi-threaded HTTP server. Optional positional args: port host thread_pool_size."
        ),
        epilog=(
            "Examples:\n"
            "  python server.py\n"
            "  python server.py 9090\n"
            "  python server.py 9090 0.0.0.0\n"
            "  python server.py 9090 0.0.0.0 32\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("port", nargs="?", type=int, default=8080, help="TCP port (default: 8080)")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("thread_pool_size", nargs="?", type=int, default=10, help="Worker threads (default: 10)")

    return parser.parse_args(argv)


def ensure_directories() -> Path:
    resources_dir = Path("resources")
    uploads_dir = resources_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return resources_dir


def send_503(sock: socket.socket) -> None:
    try:
        sock.sendall(make_error_response(503, "Service Unavailable", "Service Unavailable", close=True))
    finally:
        sock.close()


def handle_client(sock: socket.socket, addr: Tuple[str, int], resources_dir: Path, server_host: str, server_port: int) -> None:
    logger = logging.getLogger("server")
    # Keep-alive simple handling
    sock.settimeout(30.0)
    requests_handled = 0
    try:
        while requests_handled < 100 and not _shutdown_event.is_set():
            try:
                raw, leftover = receive_http_request(sock)
            except (BadRequestError, HeaderTooLargeError) as e:
                sock.sendall(make_error_response(400, "Bad Request", str(e), close=True))
                break
            except socket.timeout:
                # Idle timeout; close connection
                break

            method, path, version, headers = parse_http_request(raw)
            try:
                validate_host_header(headers, server_host, server_port)
            except HostMissingError:
                sock.sendall(make_error_response(400, "Bad Request", "Missing Host header", close=True))
                break
            except HostMismatchError:
                sock.sendall(make_error_response(403, "Forbidden", "Host mismatch", close=True))
                break

            logger.info("%s %s %s from %s:%d", method, path, version, addr[0], addr[1])

            connection_close = headers.get("connection", "").lower() == "close" or version == "HTTP/1.0"

            if method not in {"GET", "POST"}:
                resp = make_error_response(405, "Method Not Allowed", "Only GET and POST supported", close=connection_close)
                sock.sendall(resp)
                if connection_close:
                    break
                requests_handled += 1
                continue

            if method == "GET":
                # Map / to index.html
                req_path = "index.html" if path == "/" else path.lstrip("/")
                try:
                    target = safe_resolve_path(req_path, resources_dir)
                except ForbiddenError:
                    sock.sendall(make_error_response(403, "Forbidden", "Forbidden", close=connection_close))
                    if connection_close:
                        break
                    requests_handled += 1
                    continue
                if not target.exists() or not target.is_file():
                    sock.sendall(make_error_response(404, "Not Found", "Not Found", close=connection_close))
                    if connection_close:
                        break
                    requests_handled += 1
                    continue

                # Simple content-type/disp rules
                name = target.name
                ext = target.suffix.lower()
                if ext == ".html":
                    content_type = "text/html; charset=utf-8"
                    disposition = None
                elif ext in {".png", ".jpg", ".jpeg", ".txt"}:
                    content_type = "application/octet-stream"
                    disposition = f"attachment; filename=\"{name}\""
                else:
                    sock.sendall(make_error_response(415, "Unsupported Media Type", "Unsupported file type", close=connection_close))
                    if connection_close:
                        break
                    requests_handled += 1
                    continue

                data = target.read_bytes()
                headers_out = {"Content-Type": content_type}
                if disposition:
                    headers_out["Content-Disposition"] = disposition
                if not connection_close:
                    headers_out["Connection"] = "keep-alive"
                    headers_out["Keep-Alive"] = "timeout=30, max=100"
                resp = build_response(200, "OK", headers_out, data)
                sock.sendall(resp)
                if connection_close:
                    break
                requests_handled += 1
                continue

            if method == "POST":
                # Only JSON uploads, simplistic read of body if present after headers
                body = leftover  # bytes already read beyond headers
                content_type = headers.get("content-type", "").split(";")[0].strip()
                if content_type != "application/json":
                    sock.sendall(make_error_response(415, "Unsupported Media Type", "Only application/json accepted", close=connection_close))
                    if connection_close:
                        break
                    requests_handled += 1
                    continue
                # Determine content length and read remaining if needed
                try:
                    content_length = int(headers.get("content-length", "0"))
                except ValueError:
                    sock.sendall(make_error_response(400, "Bad Request", "Invalid Content-Length", close=connection_close))
                    break
                # If body is shorter than content-length, read remaining bytes
                read_remaining = max(0, content_length - len(body))
                buf = body
                while read_remaining > 0:
                    chunk = sock.recv(min(8192, read_remaining))
                    if not chunk:
                        break
                    buf += chunk
                    read_remaining -= len(chunk)

                # Save atomically
                uploads_dir = resources_dir / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                rand = secrets.token_hex(4)
                final = uploads_dir / f"upload_{ts}_{rand}.json"
                tmp = final.with_suffix(".tmp")
                json_data = json.loads(buf.decode("utf-8"))
                tmp.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
                os.replace(tmp, final)
                body_out = json.dumps({"filepath": str(final)}, ensure_ascii=False).encode("utf-8")
                headers_out = {"Content-Type": "application/json; charset=utf-8"}
                if not connection_close:
                    headers_out["Connection"] = "keep-alive"
                    headers_out["Keep-Alive"] = "timeout=30, max=100"
                resp = build_response(201, "Created", headers_out, body_out)
                sock.sendall(resp)
                if connection_close:
                    break
                requests_handled += 1
                continue

        # End while keep-alive
    finally:
        try:
            sock.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s")
    logger = logging.getLogger("server")

    # Register Ctrl+C handler to set shutdown event (more reliable on Windows)
    try:
        signal.signal(signal.SIGINT, _handle_sigint)
    except Exception:
        # Some environments may not allow setting signal handlers
        pass

    resources_dir = ensure_directories()

    print(
        f"Parsed args: port={args.port}, host={args.host}, thread_pool_size={args.thread_pool_size}"
    )

    logger.info("HTTP Server started on http://%s:%d", args.host, args.port)
    logger.info("Thread pool size: %d", args.thread_pool_size)

    pool = ThreadPool(num_workers=args.thread_pool_size, queue_max=64)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((args.host, args.port))
    server_sock.listen(50)
    server_sock.settimeout(1.0)  # short timeout to allow shutdown polling
    logger.info("Listening backlog: 50")

    try:
        while not _shutdown_event.is_set():
            try:
                conn, addr = server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                # Socket likely closed during shutdown
                break
            if not pool.try_submit(handle_client, conn, addr, resources_dir, args.host, args.port, timeout=0.01):
                logger.warning("Queue full; returning 503 to %s:%d", addr[0], addr[1])
                send_503(conn)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt; initiating shutdown")
        _shutdown_event.set()
    finally:
        try:
            server_sock.close()
        except Exception:
            pass
        pool.shutdown(wait=True)
        logger.info("Shutdown complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())