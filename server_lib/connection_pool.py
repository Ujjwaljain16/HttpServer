"""Connection pooling for better resource management."""

from __future__ import annotations

import socket
import threading
import time
from collections import deque
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class PooledConnection:
    """A pooled socket connection with metadata."""
    sock: socket.socket
    created_at: float
    last_used: float
    use_count: int
    is_healthy: bool = True


class ConnectionPool:
    """Thread-safe connection pool for socket reuse."""
    
    def __init__(self, max_connections: int = 100, max_idle_time: float = 300.0):
        self._max_connections = max_connections
        self._max_idle_time = max_idle_time
        self._lock = threading.Lock()
        self._pool: deque[PooledConnection] = deque()
        self._active_connections = 0
        self._total_created = 0
        self._total_reused = 0
        self._total_expired = 0
    
    def get_connection(self, host: str, port: int, timeout: float = 5.0) -> Optional[socket.socket]:
        """Get a connection from the pool or create a new one."""
        with self._lock:
            # Try to reuse an existing connection
            while self._pool:
                pooled_conn = self._pool.popleft()
                
                # Check if connection is still healthy and not expired
                if (pooled_conn.is_healthy and 
                    time.time() - pooled_conn.last_used < self._max_idle_time):
                    
                    # Test the connection
                    try:
                        pooled_conn.sock.settimeout(1.0)
                        # Simple test - try to get socket info
                        pooled_conn.sock.getsockname()
                        pooled_conn.last_used = time.time()
                        pooled_conn.use_count += 1
                        self._active_connections += 1
                        self._total_reused += 1
                        return pooled_conn.sock
                    except (OSError, socket.error):
                        # Connection is dead, close it
                        try:
                            pooled_conn.sock.close()
                        except:
                            pass
                        self._total_expired += 1
                        continue
                else:
                    # Connection expired, close it
                    try:
                        pooled_conn.sock.close()
                    except:
                        pass
                    self._total_expired += 1
            
            # No reusable connection found, create a new one
            if self._active_connections < self._max_connections:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    sock.connect((host, port))
                    self._active_connections += 1
                    self._total_created += 1
                    return sock
                except (OSError, socket.error):
                    return None
            
            return None
    
    def return_connection(self, sock: socket.socket) -> None:
        """Return a connection to the pool for reuse."""
        if not sock:
            return
            
        with self._lock:
            if len(self._pool) < self._max_connections:
                pooled_conn = PooledConnection(
                    sock=sock,
                    created_at=time.time(),
                    last_used=time.time(),
                    use_count=1
                )
                self._pool.append(pooled_conn)
                self._active_connections -= 1
            else:
                # Pool is full, close the connection
                try:
                    sock.close()
                except:
                    pass
                self._active_connections -= 1
    
    def close_connection(self, sock: socket.socket) -> None:
        """Close a connection without returning it to the pool."""
        if sock:
            try:
                sock.close()
            except:
                pass
            with self._lock:
                self._active_connections -= 1
    
    def cleanup_expired(self) -> int:
        """Remove expired connections from the pool."""
        with self._lock:
            current_time = time.time()
            expired_count = 0
            
            # Remove expired connections
            remaining = deque()
            while self._pool:
                pooled_conn = self._pool.popleft()
                if (current_time - pooled_conn.last_used < self._max_idle_time and 
                    pooled_conn.is_healthy):
                    remaining.append(pooled_conn)
                else:
                    try:
                        pooled_conn.sock.close()
                    except:
                        pass
                    expired_count += 1
            
            self._pool = remaining
            self._total_expired += expired_count
            return expired_count
    
    def get_stats(self) -> dict:
        """Get connection pool statistics."""
        with self._lock:
            return {
                "pool_size": len(self._pool),
                "active_connections": self._active_connections,
                "max_connections": self._max_connections,
                "total_created": self._total_created,
                "total_reused": self._total_reused,
                "total_expired": self._total_expired,
                "reuse_rate": (self._total_reused / (self._total_created + self._total_reused)) * 100 
                              if (self._total_created + self._total_reused) > 0 else 0
            }
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            while self._pool:
                pooled_conn = self._pool.popleft()
                try:
                    pooled_conn.sock.close()
                except:
                    pass
            self._active_connections = 0


# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool instance."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool()
    return _connection_pool


def cleanup_connection_pool() -> None:
    """Cleanup expired connections in the global pool."""
    if _connection_pool:
        _connection_pool.cleanup_expired()
