"""Entry point for the multi-threaded HTTP server.

Parses CLI arguments, prepares the environment, starts a TCP listener, and
accepts connections, handing them to a bounded thread pool for handling.
"""

from __future__ import annotations

import argparse
import json
import logging
from server_lib.logger import setup_logging, get_logger, log_thread_status
from server_lib.metrics import record_request_metrics, get_metrics_collector
from server_lib.metrics_endpoint import handle_metrics_request
from server_lib.rate_limiter import check_rate_limit
from server_lib.request_limiter import validate_request_size
from server_lib.cors import add_cors_headers, handle_cors_preflight
from server_lib.security_dashboard import handle_security_dashboard_request, record_security_event
import os
import secrets
import socket
import signal
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple

from server_lib.http_parser import (
    receive_http_request,
    parse_http_request,
    BadRequestError,
    HeaderTooLargeError,
)
from server_lib.response import build_response, make_error_response, make_method_not_allowed_response, make_service_unavailable_response
from server_lib.security import (
    safe_resolve_path,
    validate_host_header,
    ForbiddenError,
    HostMissingError,
    HostMismatchError,
)
from server_lib.threadpool import ThreadPool
from server_lib.utils import generate_upload_filename


def send_response_chunked(sock: socket.socket, response: bytes, chunk_size: int = 8192) -> None:
    """
    Send response data in chunks to handle large files efficiently.
    
    Args:
        sock: Socket to send data to
        response: Complete response bytes to send
        chunk_size: Size of each chunk (default 8KB)
    """
    try:
        # Send in chunks to avoid overwhelming the socket buffer
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            sock.sendall(chunk)
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error sending response chunk: {e}")
        raise


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


def send_503(sock: socket.socket, client_addr: tuple[str, int]) -> None:
    """Send 503 Service Unavailable response when thread pool is saturated.
    
    Args:
        sock: Client socket to send response to
        client_addr: Client address tuple (ip, port) for logging
    """
    logger = get_logger()
    try:
        # Send standardized 503 response with Retry-After header
        response = make_service_unavailable_response(retry_after=5, close_connection=True)
        sock.sendall(response)
        logger.warning("503 Service Unavailable sent to %s:%d (thread pool saturated)", 
                      extra_data={"client_ip": client_addr[0], "client_port": client_addr[1]})
    except Exception as e:
        logger.error("Error sending 503 to %s:%d: %s", 
                    extra_data={"client_ip": client_addr[0], "client_port": client_addr[1], "error": str(e)})
    finally:
        sock.close()


def handle_get(path: str, headers: dict, resources_dir: Path, keep_alive: bool, client_addr: str = None) -> bytes:
    # Map / to index.html
    req_path = "index.html" if path == "/" else path.lstrip("/")
    
    # Check for path traversal attempts before processing
    if ".." in req_path:
        if client_addr:
            from server_lib.security import log_security_violation
            log_security_violation(client_addr, f"GET {path} HTTP/1.1", "Path traversal detected")
        return make_error_response(403, "Forbidden", "Path traversal detected", close_connection=not keep_alive)
    
    
    try:
        target = safe_resolve_path(req_path, resources_dir, client_addr)
    except ForbiddenError:
        return make_error_response(403, "Forbidden", "Forbidden", close_connection=not keep_alive)

    if not target.exists() or not target.is_file():
        return make_error_response(404, "Not Found", "Not Found", close_connection=not keep_alive)

    name = target.name
    ext = target.suffix.lower()
    if ext == ".html":
        content_type = "text/html; charset=utf-8"
        disposition = None
    elif ext in {".png", ".jpg", ".jpeg", ".txt"}:
        content_type = "application/octet-stream"
        disposition = f"attachment; filename=\"{name}\""
    else:
        return make_error_response(415, "Unsupported Media Type", "Unsupported file type", close_connection=not keep_alive)

    # Get file size for proper handling
    file_size = target.stat().st_size
    logger = get_logger()
    
    # Use chunked reading for efficient binary transfer
    CHUNK_SIZE = 8192  # 8KB chunks as recommended for efficient transfer
    data = b""
    bytes_read = 0
    
    try:
        with target.open("rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                data += chunk
                bytes_read += len(chunk)
                
                # For very large files (>10MB), we could implement streaming here
                # For now, we'll read into memory but with proper chunking
                if bytes_read > 10 * 1024 * 1024:  # 10MB threshold
                    logger.warning(f"Large file being read: {name} ({file_size} bytes) - consider streaming for production")
                    break
                    
    except Exception as e:
        logger.error(f"Error reading file {name}: {e}")
        return make_error_response(500, "Internal Server Error", "File read error", close_connection=not keep_alive)
    
    # Validate file integrity (size check)
    if len(data) != file_size:
        logger.error(f"File size mismatch: expected {file_size}, got {len(data)} bytes for {name}")
        return make_error_response(500, "Internal Server Error", "File integrity error", close_connection=not keep_alive)
    
    # Log file serving with chunk information
    chunks_used = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE
    if file_size > 1024 * 1024:  # 1MB threshold
        logger.info(f"Serving large file: {name} ({file_size} bytes) in {chunks_used} chunks of {CHUNK_SIZE} bytes")
    else:
        logger.debug(f"Serving file: {name} ({file_size} bytes) in {chunks_used} chunks")
    headers_out = {"Content-Type": content_type}
    if disposition:
        headers_out["Content-Disposition"] = disposition
    if keep_alive:
        headers_out["Connection"] = "keep-alive"
        headers_out["Keep-Alive"] = "timeout=30, max=100"
    return build_response(200, "OK", headers_out, data)


def handle_post(path: str, headers: dict, body_bytes: bytes, resources_dir: Path, keep_alive: bool) -> bytes:
    content_type = headers.get("content-type", "").split(";")[0].strip()
    if content_type != "application/json":
        return make_error_response(415, "Unsupported Media Type", "Only application/json accepted", close_connection=not keep_alive)

    # Only allow /upload path in this iteration
    if path.rstrip("/") != "/upload":
        return make_error_response(404, "Not Found", "Not Found", close_connection=not keep_alive)

    # Parse JSON
    try:
        obj = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return make_error_response(400, "Bad Request", "Invalid JSON", close_connection=not keep_alive)

    uploads_dir = resources_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_upload_filename()
    final = uploads_dir / filename
    tmp = final.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, final)

    resp_body = json.dumps({
        "status": "success",
        "message": "File created successfully",
        "filepath": f"/uploads/{final.name}"
    }, ensure_ascii=False).encode("utf-8")
    headers_out = {"Content-Type": "application/json; charset=utf-8"}
    if keep_alive:
        headers_out["Connection"] = "keep-alive"
        headers_out["Keep-Alive"] = "timeout=30, max=100"
    return build_response(201, "Created", headers_out, resp_body)


def handle_client(sock: socket.socket, addr: Tuple[str, int], resources_dir: Path, server_host: str, server_port: int) -> None:
    """Handle a client connection with persistent connection support.
    
    State machine:
    1. Set socket timeout (30s idle timeout)
    2. Loop while under request limit (100) and not shutdown:
       a. Read HTTP request headers
       b. Parse and validate request
       c. Determine keep-alive behavior
       d. Process request (GET/POST)
       e. Send response with appropriate Connection headers
       f. Break if connection should close
       g. Increment request counter
    3. Close socket on exit
    
    Keep-alive rules:
    - HTTP/1.1: default keep-alive (unless Connection: close)
    - HTTP/1.0: default close (unless Connection: keep-alive)
    - Max 100 requests per connection
    - 30s idle timeout
    """
    logger = get_logger()
    
    # Connection state
    MAX_REQUESTS_PER_CONNECTION = 100
    IDLE_TIMEOUT = 30.0
    
    # Set idle timeout for persistent connections
    sock.settimeout(IDLE_TIMEOUT)
    requests_handled = 0
    
    logger.debug(f"Handling client {addr[0]}:{addr[1]}, max_requests={MAX_REQUESTS_PER_CONNECTION}, timeout={IDLE_TIMEOUT}s")
    
    try:
        # Persistent connection loop
        while requests_handled < MAX_REQUESTS_PER_CONNECTION and not _shutdown_event.is_set():
            try:
                raw, leftover = receive_http_request(sock)
            except (BadRequestError, HeaderTooLargeError) as e:
                sock.sendall(make_error_response(400, "Bad Request", str(e), close_connection=True))
                break
            except socket.timeout:
                # Idle timeout; close connection
                logger.debug(f"Client {addr[0]}:{addr[1]} idle timeout after {requests_handled} requests")
                break

            # Parse request
            method, path, version, headers = parse_http_request(raw)
            
            # Security checks
            client_addr = f"{addr[0]}:{addr[1]}"
            
            # 1. Rate limiting
            rate_allowed, rate_reason = check_rate_limit(addr[0])
            if not rate_allowed:
                record_security_event("rate_limit", addr[0], {"reason": rate_reason}, "high", True)
                sock.sendall(make_error_response(429, "Too Many Requests", rate_reason, close_connection=True))
                break
            
            # 2. Request size validation
            body_size = int(headers.get("content-length", "0"))
            size_valid, size_reason = validate_request_size(raw, b"" if body_size == 0 else leftover, path)
            if not size_valid:
                record_security_event("request_too_large", addr[0], {"reason": size_reason}, "medium", True)
                sock.sendall(make_error_response(413, "Payload Too Large", size_reason, close_connection=True))
                break
            
            # 3. Validate Host header
            try:
                validate_host_header(headers, server_host, server_port, client_addr)
            except HostMissingError:
                record_security_event("missing_host", addr[0], {"path": path}, "medium", True)
                sock.sendall(make_error_response(400, "Bad Request", "Missing Host header", close_connection=True))
                break
            except HostMismatchError:
                record_security_event("host_mismatch", addr[0], {"path": path, "host": headers.get("host", "none")}, "high", True)
                sock.sendall(make_error_response(403, "Forbidden", "Host mismatch", close_connection=True))
                break

            logger.info("%s %s %s from %s:%d (req #%d)", method, path, version, addr[0], addr[1], requests_handled + 1)

            # Start timing the request
            request_start_time = time.time()

            # Determine keep-alive behavior
            # HTTP/1.1: default keep-alive (unless Connection: close)
            # HTTP/1.0: default close (unless Connection: keep-alive)
            connection_header = headers.get("connection", "").lower()
            if version == "HTTP/1.0":
                keep_alive = connection_header == "keep-alive"
            else:  # HTTP/1.1
                keep_alive = connection_header != "close"

            # Handle CORS preflight requests
            if method == "OPTIONS":
                origin = headers.get("origin", "")
                request_method = headers.get("access-control-request-method", "")
                request_headers = headers.get("access-control-request-headers", "").split(",") if headers.get("access-control-request-headers") else []
                
                status_code, resp_headers = handle_cors_preflight(origin, request_method, request_headers)
                resp = build_response(status_code, "OK" if status_code == 200 else "Forbidden", resp_headers, b"")
                sock.sendall(resp)
                if not keep_alive:
                    break
                requests_handled += 1
                # Record metrics for this request
                response_time_ms = (time.time() - request_start_time) * 1000
                record_request_metrics(method, path, status_code, response_time_ms, client_addr, 0)
                continue

            # Handle metrics endpoint
            if path == "/metrics":
                status_code, resp_headers, resp_body = handle_metrics_request(path, headers)
                resp = build_response(status_code, "OK" if status_code == 200 else "Error", resp_headers, resp_body)
                sock.sendall(resp)
                if not keep_alive:
                    break
                requests_handled += 1
                # Record metrics for this request
                response_time_ms = (time.time() - request_start_time) * 1000
                record_request_metrics(method, path, status_code, response_time_ms, client_addr, len(resp_body))
                continue

            # Handle security dashboard endpoint
            if path == "/security-dashboard":
                status_code, resp_headers, resp_body = handle_security_dashboard_request(path, headers)
                resp = build_response(status_code, "OK" if status_code == 200 else "Error", resp_headers, resp_body)
                sock.sendall(resp)
                if not keep_alive:
                    break
                requests_handled += 1
                # Record metrics for this request
                response_time_ms = (time.time() - request_start_time) * 1000
                record_request_metrics(method, path, status_code, response_time_ms, client_addr, len(resp_body))
                continue

            if method not in {"GET", "POST"}:
                resp = make_method_not_allowed_response(["GET", "POST"], close_connection=not keep_alive)
                sock.sendall(resp)
                if not keep_alive:
                    break
                requests_handled += 1
                # Record metrics for this request
                response_time_ms = (time.time() - request_start_time) * 1000
                record_request_metrics(method, path, 405, response_time_ms, client_addr, len(resp))
                continue

            if method == "GET":
                resp = handle_get(path, headers, resources_dir, keep_alive, client_addr)
                # Use chunked sending for large responses (files > 1MB)
                if len(resp) > 1024 * 1024:  # 1MB threshold
                    send_response_chunked(sock, resp)
                else:
                    sock.sendall(resp)
                if not keep_alive:
                    break
                requests_handled += 1
                # Record metrics for this request
                response_time_ms = (time.time() - request_start_time) * 1000
                record_request_metrics(method, path, 200, response_time_ms, client_addr, len(resp))
                continue

            if method == "POST":
                # Determine content length and read remaining if needed
                try:
                    content_length = int(headers.get("content-length", "0"))
                except ValueError:
                    resp = make_error_response(400, "Bad Request", "Invalid Content-Length", close_connection=not keep_alive)
                    sock.sendall(resp)
                    break
                body = leftover
                read_remaining = max(0, content_length - len(body))
                buf = body
                while read_remaining > 0:
                    chunk = sock.recv(min(8192, read_remaining))
                    if not chunk:
                        break
                    buf += chunk
                    read_remaining -= len(chunk)

                resp = handle_post(path, headers, buf, resources_dir, keep_alive)
                sock.sendall(resp)
                if not keep_alive:
                    break
                requests_handled += 1
                # Record metrics for this request
                response_time_ms = (time.time() - request_start_time) * 1000
                record_request_metrics(method, path, 201, response_time_ms, client_addr, len(resp))
                continue

        # End persistent connection loop
        logger.debug(f"Client {addr[0]}:{addr[1]} connection closed after {requests_handled} requests")
        
    except Exception as e:
        logger.error(f"Error handling client {addr[0]}:{addr[1]}: {e}")
    finally:
        # Always close socket
        try:
            sock.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Setup enhanced logging
    logger = setup_logging(level=logging.INFO)

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

    # Register main thread
    logger.register_thread("MainThread", "main", {"port": args.port, "host": args.host})
    
    logger.info("HTTP Server started on http://%s:%d", args.host, args.port)
    logger.info("Thread pool size: %d", args.thread_pool_size)

    pool = ThreadPool(num_workers=args.thread_pool_size, queue_max=32)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((args.host, args.port))
    server_sock.listen(50)
    server_sock.settimeout(1.0)  # short timeout to allow shutdown polling
    logger.info("Listening backlog: 50")

    # Add periodic thread status logging
    last_status_log = time.time()
    STATUS_LOG_INTERVAL = 30.0  # Log thread status every 30 seconds

    try:
        while not _shutdown_event.is_set():
            try:
                conn, addr = server_sock.accept()
            except socket.timeout:
                # Log thread status periodically
                current_time = time.time()
                if current_time - last_status_log >= STATUS_LOG_INTERVAL:
                    log_thread_status()
                    last_status_log = current_time
                continue
            except OSError:
                # Socket likely closed during shutdown
                break
            if not pool.try_submit(handle_client, conn, addr, resources_dir, args.host, args.port, timeout=0.1):
                logger.warning("Thread pool queue full; rejecting connection from %s:%d", addr[0], addr[1])
                send_503(conn, addr)
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