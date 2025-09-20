"""Performance metrics and monitoring utilities."""

from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    method: str
    path: str
    status_code: int
    response_time_ms: float
    client_ip: str
    timestamp: datetime
    content_length: int = 0


class MetricsCollector:
    """Thread-safe metrics collector for HTTP server performance monitoring."""
    
    def __init__(self, max_history: int = 10000):
        self._lock = threading.Lock()
        self._max_history = max_history
        
        # Request metrics
        self._request_history: deque = deque(maxlen=max_history)
        self._response_times: deque = deque(maxlen=1000)  # Last 1000 response times
        
        # Counters
        self._total_requests = 0
        self._total_errors = 0
        self._total_bytes_sent = 0
        
        # Per-endpoint metrics
        self._endpoint_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'requests': 0, 'errors': 0, 'total_time': 0.0, 'min_time': float('inf'), 'max_time': 0.0
        })
        
        # Per-IP metrics
        self._ip_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'requests': 0, 'errors': 0, 'last_seen': None
        })
        
        # Status code counters
        self._status_codes: Dict[int, int] = defaultdict(int)
        
        # Server start time
        self._start_time = time.time()
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record metrics for a completed request."""
        with self._lock:
            # Update counters
            self._total_requests += 1
            self._total_bytes_sent += metrics.content_length
            self._status_codes[metrics.status_code] += 1
            
            if metrics.status_code >= 400:
                self._total_errors += 1
            
            # Store in history
            self._request_history.append(metrics)
            self._response_times.append(metrics.response_time_ms)
            
            # Update endpoint stats
            endpoint_key = f"{metrics.method} {metrics.path}"
            endpoint_stats = self._endpoint_stats[endpoint_key]
            endpoint_stats['requests'] += 1
            endpoint_stats['total_time'] += metrics.response_time_ms
            endpoint_stats['min_time'] = min(endpoint_stats['min_time'], metrics.response_time_ms)
            endpoint_stats['max_time'] = max(endpoint_stats['max_time'], metrics.response_time_ms)
            
            if metrics.status_code >= 400:
                endpoint_stats['errors'] += 1
            
            # Update IP stats
            ip_stats = self._ip_stats[metrics.client_ip]
            ip_stats['requests'] += 1
            ip_stats['last_seen'] = metrics.timestamp
            if metrics.status_code >= 400:
                ip_stats['errors'] += 1
    
    def get_system_metrics(self) -> Dict:
        """Get system resource metrics if psutil is available."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        try:
            process = psutil.Process()
            return {
                "memory": {
                    "rss": process.memory_info().rss,  # Resident Set Size
                    "vms": process.memory_info().vms,  # Virtual Memory Size
                    "percent": process.memory_percent(),
                    "available": psutil.virtual_memory().available
                },
                "cpu": {
                    "percent": process.cpu_percent(),
                    "count": psutil.cpu_count()
                },
                "disk": {
                    "usage": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else 0
                }
            }
        except Exception as e:
            return {"error": f"Failed to get system metrics: {e}"}
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics."""
        with self._lock:
            if not self._response_times:
                return {
                    "total_requests": self._total_requests,
                    "total_errors": self._total_errors,
                    "error_rate": 0.0,
                    "uptime_seconds": time.time() - self._start_time,
                    "avg_response_time_ms": 0.0,
                    "min_response_time_ms": 0.0,
                    "max_response_time_ms": 0.0,
                    "total_bytes_sent": self._total_bytes_sent
                }
            
            response_times = list(self._response_times)
            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate": (self._total_errors / self._total_requests) * 100 if self._total_requests > 0 else 0.0,
                "uptime_seconds": time.time() - self._start_time,
                "avg_response_time_ms": sum(response_times) / len(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "total_bytes_sent": self._total_bytes_sent,
                "requests_per_second": self._total_requests / (time.time() - self._start_time) if time.time() > self._start_time else 0
            }
    
    def get_endpoint_stats(self) -> Dict:
        """Get statistics per endpoint."""
        with self._lock:
            result = {}
            for endpoint, stats in self._endpoint_stats.items():
                if stats['requests'] > 0:
                    result[endpoint] = {
                        "requests": stats['requests'],
                        "errors": stats['errors'],
                        "avg_response_time_ms": stats['total_time'] / stats['requests'],
                        "min_response_time_ms": stats['min_time'] if stats['min_time'] != float('inf') else 0,
                        "max_response_time_ms": stats['max_time'],
                        "error_rate": (stats['errors'] / stats['requests']) * 100
                    }
            return result
    
    def get_ip_stats(self) -> Dict:
        """Get statistics per IP address."""
        with self._lock:
            result = {}
            for ip, stats in self._ip_stats.items():
                result[ip] = {
                    "requests": stats['requests'],
                    "errors": stats['errors'],
                    "last_seen": stats['last_seen'].isoformat() if stats['last_seen'] else None,
                    "error_rate": (stats['errors'] / stats['requests']) * 100 if stats['requests'] > 0 else 0
                }
            return result
    
    def get_status_code_stats(self) -> Dict:
        """Get status code distribution."""
        with self._lock:
            return dict(self._status_codes)
    
    def get_recent_requests(self, limit: int = 100) -> List[Dict]:
        """Get recent request details."""
        with self._lock:
            recent = list(self._request_history)[-limit:]
            return [
                {
                    "method": req.method,
                    "path": req.path,
                    "status_code": req.status_code,
                    "response_time_ms": req.response_time_ms,
                    "client_ip": req.client_ip,
                    "timestamp": req.timestamp.isoformat(),
                    "content_length": req.content_length
                }
                for req in recent
            ]


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_request_metrics(method: str, path: str, status_code: int, 
                          response_time_ms: float, client_ip: str, 
                          content_length: int = 0) -> None:
    """Convenience function to record request metrics."""
    metrics = RequestMetrics(
        method=method,
        path=path,
        status_code=status_code,
        response_time_ms=response_time_ms,
        client_ip=client_ip,
        timestamp=datetime.now(),
        content_length=content_length
    )
    get_metrics_collector().record_request(metrics)
