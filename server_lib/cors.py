"""CORS (Cross-Origin Resource Sharing) support."""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class CORSConfig:
    """Configuration for CORS headers."""
    allowed_origins: Set[str] = None  # None means allow all
    allowed_methods: Set[str] = None  # None means use request method
    allowed_headers: Set[str] = None  # None means allow all
    exposed_headers: Set[str] = None
    allow_credentials: bool = False
    max_age: int = 86400  # 24 hours
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = {"*"}
        if self.allowed_methods is None:
            self.allowed_methods = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"}
        if self.allowed_headers is None:
            self.allowed_headers = {"*"}
        if self.exposed_headers is None:
            self.exposed_headers = set()


class CORSHandler:
    """CORS request handler."""
    
    def __init__(self, config: CORSConfig = None):
        self._config = config or CORSConfig()
    
    def get_cors_headers(self, origin: str, method: str, request_headers: List[str]) -> Dict[str, str]:
        """
        Generate CORS headers for a request.
        
        Args:
            origin: Origin header from request
            method: HTTP method
            request_headers: List of headers from Access-Control-Request-Headers
            
        Returns:
            Dictionary of CORS headers to include in response
        """
        headers = {}
        
        # Check if origin is allowed
        if self._is_origin_allowed(origin):
            headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self._config.allowed_origins:
            headers["Access-Control-Allow-Origin"] = "*"
        else:
            # Origin not allowed, return minimal headers
            return {}
        
        # Add credentials header if enabled
        if self._config.allow_credentials and origin != "*":
            headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add allowed methods
        if method in self._config.allowed_methods:
            methods_str = ", ".join(sorted(self._config.allowed_methods))
            headers["Access-Control-Allow-Methods"] = methods_str
        
        # Add allowed headers
        if self._are_headers_allowed(request_headers):
            if "*" in self._config.allowed_headers:
                headers["Access-Control-Allow-Headers"] = "*"
            else:
                headers_str = ", ".join(sorted(self._config.allowed_headers))
                headers["Access-Control-Allow-Headers"] = headers_str
        
        # Add exposed headers
        if self._config.exposed_headers:
            exposed_str = ", ".join(sorted(self._config.exposed_headers))
            headers["Access-Control-Expose-Headers"] = exposed_str
        
        # Add max age
        headers["Access-Control-Max-Age"] = str(self._config.max_age)
        
        return headers
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if the origin is allowed."""
        if not origin:
            return False
        
        if "*" in self._config.allowed_origins:
            return True
        
        return origin in self._config.allowed_origins
    
    def _are_headers_allowed(self, request_headers: List[str]) -> bool:
        """Check if the requested headers are allowed."""
        if not request_headers:
            return True
        
        if "*" in self._config.allowed_headers:
            return True
        
        return all(header.lower() in {h.lower() for h in self._config.allowed_headers} 
                  for header in request_headers)
    
    def handle_preflight(self, origin: str, method: str, request_headers: List[str]) -> tuple[int, Dict[str, str]]:
        """
        Handle a CORS preflight request.
        
        Returns:
            (status_code, headers)
        """
        if not origin:
            return 400, {"Content-Type": "text/plain"}
        
        cors_headers = self.get_cors_headers(origin, method, request_headers)
        
        if not cors_headers:
            return 403, {"Content-Type": "text/plain"}
        
        # Preflight requests should return 200 with CORS headers
        return 200, cors_headers


# Global CORS handler instance
_cors_handler: Optional[CORSHandler] = None


def get_cors_handler() -> CORSHandler:
    """Get the global CORS handler instance."""
    global _cors_handler
    if _cors_handler is None:
        _cors_handler = CORSHandler()
    return _cors_handler


def add_cors_headers(headers: Dict[str, str], origin: str, method: str, request_headers: List[str] = None) -> Dict[str, str]:
    """Add CORS headers to a response."""
    cors_headers = get_cors_handler().get_cors_headers(origin, method, request_headers or [])
    return {**headers, **cors_headers}


def handle_cors_preflight(origin: str, method: str, request_headers: List[str] = None) -> tuple[int, Dict[str, str]]:
    """Handle a CORS preflight request."""
    return get_cors_handler().handle_preflight(origin, method, request_headers or [])
