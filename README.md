# Multi-threaded HTTP Server

A minimal, educational multi-threaded HTTP/1.1 server written in Python using low-level sockets.

## Features (first iteration)
- TCP sockets, manual HTTP parsing
- Fixed-size thread pool with bounded queue
- Serves static files from `resources/` (index.html at `/`)
- JSON POST upload to `resources/uploads/` with atomic writes
- Basic security: Host header validation, path traversal protection
- Keep-Alive headers and simple limits (timeout=30s, max=100)

## Requirements
- Python 3.11+

## Run
```bash
python server.py                 # defaults: 127.0.0.1:8080, 10 threads
python server.py 9090
python server.py 9090 0.0.0.0 32
```

You should see logs like:
```
[YYYY-MM-DD HH:MM:SS] HTTP Server started on http://127.0.0.1:8080
Thread pool size: 10
```

## Quick tests
- GET root:
```bash
curl http://127.0.0.1:8080/
```
- Forbidden traversal:
```bash
printf 'GET /../etc/passwd HTTP/1.1\r\nHost: localhost:8080\r\n\r\n' | nc 127.0.0.1 8080
```
- Missing Host (should be 400):
```bash
printf 'GET / HTTP/1.1\r\n\r\n' | nc 127.0.0.1 8080 -N
```
- JSON upload (created under resources/uploads/):
```bash
curl -v -H 'Content-Type: application/json' --data '{"hello": "world"}' http://127.0.0.1:8080/upload
```

## Tests
Install pytest and run:
```bash
pip install pytest
pytest tests/
```

## Project Structure
```
.
├─ server.py
├─ server_lib/
│  ├─ __init__.py
│  ├─ http_parser.py
│  ├─ response.py
│  ├─ security.py
│  └─ threadpool.py
├─ resources/
│  ├─ index.html
│  ├─ about.html
│  ├─ contact.html
│  ├─ sample.txt
│  ├─ logo.png
│  ├─ big.png
│  ├─ photo.jpg
│  ├─ photo2.jpg
│  └─ uploads/
├─ tests/
│  ├─ test_http_parser.py
│  ├─ test_security.py
│  └─ integration.py
├─ Dockerfile
└─ .gitignore
```

## Known limitations
- No MIME type inference beyond basic rules.
- No range requests or chunked encoding yet.
- Limited error pages and no directory listing.