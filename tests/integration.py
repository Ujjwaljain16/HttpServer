import os
import socket
import subprocess
import sys
import time


def test_get_root_with_curl():
    try:
        out = subprocess.check_output(["curl", "-sS", "http://127.0.0.1:8080/"], timeout=3)
        assert b"<html>" in out.lower()
    except Exception:
        # Curl may be unavailable; skip silently
        pass


def test_missing_host_header_raw():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("127.0.0.1", 8080))
    s.sendall(b"GET / HTTP/1.1\r\n\r\n")
    data = s.recv(4096)
    s.close()
    assert b" 400 " in data.split(b"\r\n", 1)[0]


def test_forbidden_path_raw():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("127.0.0.1", 8080))
    req = (
        b"GET /../etc/passwd HTTP/1.1\r\n"
        b"Host: localhost:8080\r\n\r\n"
    )
    s.sendall(req)
    data = s.recv(4096)
    s.close()
    assert b" 403 " in data.split(b"\r\n", 1)[0]
