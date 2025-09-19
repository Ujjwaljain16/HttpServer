from pathlib import Path
import json

from server import handle_post


def parse_head(resp: bytes):
    head, body = resp.split(b"\r\n\r\n", 1)
    status = head.split(b"\r\n", 1)[0]
    headers = {}
    for line in head.split(b"\r\n")[1:]:
        if not line:
            continue
        k, v = line.split(b":", 1)
        headers[k.decode("latin-1").lower()] = v.strip().decode("latin-1")
    return status, headers, body


def test_post_valid_json(tmp_path: Path):
    resources = tmp_path / "resources"
    (resources / "uploads").mkdir(parents=True)
    body = json.dumps({"a": 1}).encode("utf-8")
    headers = {"content-type": "application/json"}
    resp = handle_post("/upload", headers, body, resources, keep_alive=False)
    status, hdrs, body_out = parse_head(resp)
    assert b" 201 " in status
    data = json.loads(body_out.decode("utf-8"))
    assert data["filepath"].startswith("/uploads/")


def test_post_invalid_json(tmp_path: Path):
    resources = tmp_path / "resources"
    (resources / "uploads").mkdir(parents=True)
    body = b"{"  # invalid
    headers = {"content-type": "application/json"}
    resp = handle_post("/upload", headers, body, resources, keep_alive=False)
    status, _, _ = parse_head(resp)
    assert b" 400 " in status


def test_post_wrong_content_type(tmp_path: Path):
    resources = tmp_path / "resources"
    (resources / "uploads").mkdir(parents=True)
    body = b"abc"
    headers = {"content-type": "text/plain"}
    resp = handle_post("/upload", headers, body, resources, keep_alive=False)
    status, _, _ = parse_head(resp)
    assert b" 415 " in status
