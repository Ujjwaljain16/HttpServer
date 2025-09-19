from pathlib import Path

from server import handle_get


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


def test_get_root_html(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    resp = handle_get("/", {}, resources, keep_alive=False)
    status, headers, body = parse_head(resp)
    assert b" 200 " in status
    assert headers["content-type"].startswith("text/html")
    assert b"<html>ok</html>" in body


def test_get_binary_download(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir()
    data = b"\x00\x01\x02"
    (resources / "logo.png").write_bytes(data)
    resp = handle_get("/logo.png", {}, resources, keep_alive=True)
    status, headers, body = parse_head(resp)
    assert b" 200 " in status
    assert headers["content-type"] == "application/octet-stream"
    assert headers["content-disposition"].startswith("attachment;")
    assert body == data


def test_get_unsupported_type(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "file.bin").write_bytes(b"abc")
    resp = handle_get("/file.bin", {}, resources, keep_alive=False)
    status, headers, body = parse_head(resp)
    assert b" 415 " in status
