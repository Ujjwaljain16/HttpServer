"""Request size limiting for DoS protection."""

from __future__ import annotations

import threading
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RequestLimitConfig:
    """Configuration for request size limits."""
    max_header_size: int = 8192  # Max HTTP header size
    max_body_size: int = 10 * 1024 * 1024  # 10MB max body size
    max_url_length: int = 2048  # Max URL length
    max_headers_count: int = 100  # Max number of headers
    max_header_name_length: int = 256  # Max header name length
    max_header_value_length: int = 4096  # Max header value length


class RequestLimiter:
    """Thread-safe request size limiter."""
    
    def __init__(self, config: RequestLimitConfig = None):
        self._config = config or RequestLimitConfig()
        self._lock = threading.Lock()
        
        # Statistics
        self._total_requests = 0
        self._rejected_requests = 0
        self._rejection_reasons: Dict[str, int] = {}
    
    def validate_request_size(self, headers: bytes, body: bytes, url: str) -> tuple[bool, str]:
        """
        Validate request size against limits.
        
        Returns:
            (is_valid, reason)
        """
        with self._lock:
            self._total_requests += 1
            
            # Check header size
            if len(headers) > self._config.max_header_size:
                self._rejected_requests += 1
                self._rejection_reasons["header_too_large"] = self._rejection_reasons.get("header_too_large", 0) + 1
                return False, f"Header too large: {len(headers)} > {self._config.max_header_size} bytes"
            
            # Check body size
            if len(body) > self._config.max_body_size:
                self._rejected_requests += 1
                self._rejection_reasons["body_too_large"] = self._rejection_reasons.get("body_too_large", 0) + 1
                return False, f"Body too large: {len(body)} > {self._config.max_body_size} bytes"
            
            # Check URL length
            if len(url) > self._config.max_url_length:
                self._rejected_requests += 1
                self._rejection_reasons["url_too_long"] = self._rejection_reasons.get("url_too_long", 0) + 1
                return False, f"URL too long: {len(url)} > {self._config.max_url_length} characters"
            
            # Parse and validate headers
            try:
                header_text = headers.decode('latin-1')
                header_lines = header_text.split('\r\n')
                
                # Skip request line, count actual headers
                header_count = 0
                for line in header_lines[1:]:  # Skip request line
                    if not line.strip():
                        break  # End of headers
                    if ':' in line:
                        header_count += 1
                        name, value = line.split(':', 1)
                        name = name.strip()
                        value = value.strip()
                        
                        # Check header name length
                        if len(name) > self._config.max_header_name_length:
                            self._rejected_requests += 1
                            self._rejection_reasons["header_name_too_long"] = self._rejection_reasons.get("header_name_too_long", 0) + 1
                            return False, f"Header name too long: {len(name)} > {self._config.max_header_name_length} characters"
                        
                        # Check header value length
                        if len(value) > self._config.max_header_value_length:
                            self._rejected_requests += 1
                            self._rejection_reasons["header_value_too_long"] = self._rejection_reasons.get("header_value_too_long", 0) + 1
                            return False, f"Header value too long: {len(value)} > {self._config.max_header_value_length} characters"
                
                # Check header count
                if header_count > self._config.max_headers_count:
                    self._rejected_requests += 1
                    self._rejection_reasons["too_many_headers"] = self._rejection_reasons.get("too_many_headers", 0) + 1
                    return False, f"Too many headers: {header_count} > {self._config.max_headers_count}"
                
            except Exception as e:
                self._rejected_requests += 1
                self._rejection_reasons["header_parse_error"] = self._rejection_reasons.get("header_parse_error", 0) + 1
                return False, f"Header parse error: {e}"
            
            return True, "OK"
    
    def get_stats(self) -> Dict:
        """Get request limiter statistics."""
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "rejected_requests": self._rejected_requests,
                "rejection_rate": (self._rejected_requests / self._total_requests) * 100 if self._total_requests > 0 else 0,
                "rejection_reasons": dict(self._rejection_reasons),
                "config": {
                    "max_header_size": self._config.max_header_size,
                    "max_body_size": self._config.max_body_size,
                    "max_url_length": self._config.max_url_length,
                    "max_headers_count": self._config.max_headers_count,
                    "max_header_name_length": self._config.max_header_name_length,
                    "max_header_value_length": self._config.max_header_value_length
                }
            }


# Global request limiter instance
_request_limiter: Optional[RequestLimiter] = None


def get_request_limiter() -> RequestLimiter:
    """Get the global request limiter instance."""
    global _request_limiter
    if _request_limiter is None:
        _request_limiter = RequestLimiter()
    return _request_limiter


def validate_request_size(headers: bytes, body: bytes, url: str) -> tuple[bool, str]:
    """Convenience function to validate request size."""
    return get_request_limiter().validate_request_size(headers, body, url)
