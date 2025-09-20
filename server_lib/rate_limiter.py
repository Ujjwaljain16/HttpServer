"""Rate limiting implementation for DoS protection."""

from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 120  # Increased for testing
    requests_per_hour: int = 2000   # Increased for testing
    burst_limit: int = 30  # Increased for testing
    burst_window: float = 2.0  # Increased window
    block_duration: float = 60.0  # Reduced block duration


class RateLimiter:
    """Thread-safe rate limiter with multiple time windows."""
    
    def __init__(self, config: RateLimitConfig = None):
        self._config = config or RateLimitConfig()
        self._lock = threading.Lock()
        
        # Per-IP tracking
        self._ip_data: Dict[str, Dict[str, deque]] = defaultdict(lambda: {
            'requests': deque(),  # Timestamps of requests
            'burst_requests': deque(),  # Recent requests for burst detection
            'blocked_until': 0.0  # Timestamp when block expires
        })
        
        # Global statistics
        self._total_requests = 0
        self._blocked_requests = 0
        self._rate_limited_ips = set()
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, str]:
        """
        Check if a request from the given IP is allowed.
        
        Returns:
            (is_allowed, reason)
        """
        current_time = time.time()
        
        with self._lock:
            self._total_requests += 1
            ip_data = self._ip_data[client_ip]
            
            # Check if IP is currently blocked
            if current_time < ip_data['blocked_until']:
                self._blocked_requests += 1
                self._rate_limited_ips.add(client_ip)
                remaining_block = ip_data['blocked_until'] - current_time
                return False, f"Rate limited. Try again in {remaining_block:.1f} seconds"
            
            # Clean old requests outside time windows
            self._clean_old_requests(ip_data, current_time)
            
            # Check burst limit (short-term)
            if len(ip_data['burst_requests']) >= self._config.burst_limit:
                self._block_ip(ip_data, current_time)
                self._blocked_requests += 1
                self._rate_limited_ips.add(client_ip)
                return False, f"Burst limit exceeded ({self._config.burst_limit} requests in {self._config.burst_window}s)"
            
            # Check per-minute limit
            minute_ago = current_time - 60
            recent_requests = sum(1 for req_time in ip_data['requests'] if req_time > minute_ago)
            if recent_requests >= self._config.requests_per_minute:
                self._block_ip(ip_data, current_time)
                self._blocked_requests += 1
                self._rate_limited_ips.add(client_ip)
                return False, f"Rate limit exceeded ({self._config.requests_per_minute} requests per minute)"
            
            # Check per-hour limit
            hour_ago = current_time - 3600
            hourly_requests = sum(1 for req_time in ip_data['requests'] if req_time > hour_ago)
            if hourly_requests >= self._config.requests_per_hour:
                self._block_ip(ip_data, current_time)
                self._blocked_requests += 1
                self._rate_limited_ips.add(client_ip)
                return False, f"Rate limit exceeded ({self._config.requests_per_hour} requests per hour)"
            
            # Record this request
            ip_data['requests'].append(current_time)
            ip_data['burst_requests'].append(current_time)
            
            return True, "OK"
    
    def _clean_old_requests(self, ip_data: Dict[str, deque], current_time: float) -> None:
        """Remove old requests outside time windows."""
        # Clean requests older than 1 hour
        hour_ago = current_time - 3600
        while ip_data['requests'] and ip_data['requests'][0] < hour_ago:
            ip_data['requests'].popleft()
        
        # Clean burst requests older than burst window
        burst_cutoff = current_time - self._config.burst_window
        while ip_data['burst_requests'] and ip_data['burst_requests'][0] < burst_cutoff:
            ip_data['burst_requests'].popleft()
    
    def _block_ip(self, ip_data: Dict[str, deque], current_time: float) -> None:
        """Block an IP for the configured duration."""
        ip_data['blocked_until'] = current_time + self._config.block_duration
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self._lock:
            current_time = time.time()
            active_ips = len([ip for ip, data in self._ip_data.items() 
                            if current_time < data['blocked_until']])
            
            return {
                "total_requests": self._total_requests,
                "blocked_requests": self._blocked_requests,
                "block_rate": (self._blocked_requests / self._total_requests) * 100 if self._total_requests > 0 else 0,
                "currently_blocked_ips": active_ips,
                "total_tracked_ips": len(self._ip_data),
                "rate_limited_ips_count": len(self._rate_limited_ips)
            }
    
    def get_ip_stats(self, client_ip: str) -> Dict:
        """Get statistics for a specific IP."""
        with self._lock:
            if client_ip not in self._ip_data:
                return {"error": "IP not found"}
            
            ip_data = self._ip_data[client_ip]
            current_time = time.time()
            
            # Count recent requests
            minute_ago = current_time - 60
            hour_ago = current_time - 3600
            
            recent_requests = sum(1 for req_time in ip_data['requests'] if req_time > minute_ago)
            hourly_requests = sum(1 for req_time in ip_data['requests'] if req_time > hour_ago)
            
            return {
                "ip": client_ip,
                "total_requests": len(ip_data['requests']),
                "recent_requests_1min": recent_requests,
                "recent_requests_1hour": hourly_requests,
                "is_blocked": current_time < ip_data['blocked_until'],
                "blocked_until": ip_data['blocked_until'] if ip_data['blocked_until'] > 0 else None,
                "burst_requests": len(ip_data['burst_requests'])
            }
    
    def unblock_ip(self, client_ip: str) -> bool:
        """Manually unblock an IP address."""
        with self._lock:
            if client_ip in self._ip_data:
                self._ip_data[client_ip]['blocked_until'] = 0.0
                self._rate_limited_ips.discard(client_ip)
                return True
            return False
    
    def cleanup_old_data(self, max_age_hours: int = 24) -> int:
        """Remove data for IPs that haven't made requests in the specified time."""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            to_remove = []
            for ip, data in self._ip_data.items():
                if not data['requests'] or data['requests'][-1] < cutoff_time:
                    to_remove.append(ip)
            
            for ip in to_remove:
                del self._ip_data[ip]
                self._rate_limited_ips.discard(ip)
            
            return len(to_remove)


# Global rate limiter instance
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit(client_ip: str) -> Tuple[bool, str]:
    """Convenience function to check rate limit."""
    return get_rate_limiter().is_allowed(client_ip)
