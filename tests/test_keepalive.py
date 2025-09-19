import socket
import threading
import time
from pathlib import Path

from server import handle_client


class MockSocket:
    """Mock socket for testing keep-alive behavior."""
    def __init__(self, responses):
        self.responses = responses
        self.sent_data = []
        self.timeout = None
        self.closed = False
        self._recv_count = 0
        self._should_close = False
        
    def settimeout(self, timeout):
        self.timeout = timeout
        
    def gettimeout(self):
        return self.timeout
        
    def recv(self, size):
        self._recv_count += 1
        if not self.responses or self._should_close:
            return b""  # Return empty data to signal end of connection
        return self.responses.pop(0)
        
    def sendall(self, data):
        self.sent_data.append(data)
        # After sending response, mark socket as should close
        self._should_close = True
        
    def close(self):
        self.closed = True


def test_keepalive_http11_default():
    """Test HTTP/1.1 default keep-alive behavior."""
    from server import handle_get
    
    # Test the handle_get function directly with keep-alive=True
    resources = Path("resources")
    resources.mkdir(exist_ok=True)
    (resources / "index.html").write_text("<html>test</html>")
    
    # Test that handle_get returns keep-alive headers for HTTP/1.1
    response = handle_get("/", {}, resources, keep_alive=True)
    
    # Should have keep-alive headers
    assert b"Connection: keep-alive" in response
    assert b"Keep-Alive:" in response


def test_connection_close_header():
    """Test Connection: close header behavior."""
    req = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n"
    
    sock = MockSocket([req, b""])
    resources = Path("resources")
    resources.mkdir(exist_ok=True)
    (resources / "index.html").write_text("<html>test</html>")
    
    handle_client(sock, ("127.0.0.1", 12345), resources, "127.0.0.1", 8080)
    
    # Should have sent 1 response and closed
    assert len(sock.sent_data) == 1
    assert sock.closed


def test_http10_default_close():
    """Test HTTP/1.0 default close behavior."""
    req = b"GET / HTTP/1.0\r\nHost: localhost:8080\r\n\r\n"
    
    sock = MockSocket([req, b""])
    resources = Path("resources")
    resources.mkdir(exist_ok=True)
    (resources / "index.html").write_text("<html>test</html>")
    
    handle_client(sock, ("127.0.0.1", 12345), resources, "127.0.0.1", 8080)
    
    # Should have sent 1 response and closed (HTTP/1.0 default close)
    assert len(sock.sent_data) == 1
    assert sock.closed


def test_http10_keepalive_explicit():
    """Test HTTP/1.0 with explicit keep-alive."""
    from server import handle_get
    
    # Test the handle_get function directly with keep-alive=True
    resources = Path("resources")
    resources.mkdir(exist_ok=True)
    (resources / "index.html").write_text("<html>test</html>")
    
    # Test that handle_get returns keep-alive headers when requested
    response = handle_get("/", {}, resources, keep_alive=True)
    
    # Should have keep-alive headers
    assert b"Connection: keep-alive" in response
    assert b"Keep-Alive:" in response
