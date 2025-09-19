import os
import sys
import time
import json
import socket
import subprocess
from pathlib import Path


SERVER_CMD = [sys.executable, "server.py", "8080", "127.0.0.1", "4"]
BASE_URL = ("127.0.0.1", 8080)
ROOT = Path(__file__).resolve().parents[1]


def wait_for_port(host, port, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def http_raw(request_bytes: bytes) -> bytes:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(BASE_URL)
    s.sendall(request_bytes)
    # Read until header terminator
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
        idx = buf.find(b"\r\n\r\n")
        if idx != -1:
            head = buf[: idx + 4]
            body = buf[idx + 4 :]
            # Determine body length
            headers = head.decode("latin-1").split("\r\n")
            clen = 0
            for line in headers:
                if line.lower().startswith("content-length:"):
                    try:
                        clen = int(line.split(":", 1)[1].strip())
                    except Exception:
                        clen = 0
                    break
            # Read remaining body bytes if any
            while len(body) < clen:
                part = s.recv(4096)
                if not part:
                    break
                body += part
            s.close()
            return head + body
    s.close()
    return buf


def check_get_root():
    req = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
    resp = http_raw(req)
    return b" 200 " in resp.split(b"\r\n", 1)[0] and b"<html>" in resp.lower()


def check_missing_host():
    req = b"GET / HTTP/1.1\r\n\r\n"
    resp = http_raw(req)
    return b" 400 " in resp.split(b"\r\n", 1)[0]


def check_forbidden_traversal():
    req = b"GET /../etc/passwd HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
    resp = http_raw(req)
    return b" 403 " in resp.split(b"\r\n", 1)[0]


def check_post_upload():
    body = json.dumps({"hello": "world"}).encode("utf-8")
    req = (
        b"POST /upload HTTP/1.1\r\n"
        b"Host: localhost:8080\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode("latin-1")
        + body
    )
    resp = http_raw(req)
    if b" 201 " not in resp.split(b"\r\n", 1)[0]:
        return False
    head, body_bytes = resp.split(b"\r\n\r\n", 1)
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return False
    return isinstance(payload.get("filepath"), str)


def main():
    print("Starting server ...")
    proc = subprocess.Popen(SERVER_CMD, cwd=str(ROOT))
    try:
        if not wait_for_port(*BASE_URL):
            print("Server did not start listening in time", file=sys.stderr)
            return 1
        # slight delay to allow thread pool warm-up
        time.sleep(0.2)
        results = {
            "GET /": check_get_root(),
            "Missing Host": check_missing_host(),
            "Forbidden traversal": check_forbidden_traversal(),
            "POST upload": check_post_upload(),
        }
        for name, ok in results.items():
            print(f"[{'OK' if ok else 'FAIL'}] {name}")
        rc = 0 if all(results.values()) else 1
        return rc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
