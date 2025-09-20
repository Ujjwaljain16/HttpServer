"""Metrics endpoint for Prometheus-style monitoring."""

from __future__ import annotations

import json
from typing import Dict, Any
from server_lib.metrics import get_metrics_collector
from server_lib.connection_pool import get_connection_pool
from server_lib.threadpool import ThreadPool


def generate_prometheus_metrics() -> str:
    """Generate Prometheus-formatted metrics."""
    metrics_collector = get_metrics_collector()
    thread_pool = get_connection_pool()  # This should be the actual thread pool
    
    # Get all metrics
    summary_stats = metrics_collector.get_summary_stats()
    endpoint_stats = metrics_collector.get_endpoint_stats()
    ip_stats = metrics_collector.get_ip_stats()
    status_codes = metrics_collector.get_status_code_stats()
    system_metrics = metrics_collector.get_system_metrics()
    
    # Build Prometheus format
    lines = []
    
    # HTTP request metrics
    lines.append("# HELP http_requests_total Total number of HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    lines.append(f"http_requests_total {summary_stats['total_requests']}")
    
    lines.append("# HELP http_requests_errors_total Total number of HTTP request errors")
    lines.append("# TYPE http_requests_errors_total counter")
    lines.append(f"http_requests_errors_total {summary_stats['total_errors']}")
    
    lines.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
    lines.append("# TYPE http_request_duration_seconds histogram")
    lines.append(f"http_request_duration_seconds_sum {summary_stats['avg_response_time_ms'] * summary_stats['total_requests'] / 1000}")
    lines.append(f"http_request_duration_seconds_count {summary_stats['total_requests']}")
    
    lines.append("# HELP http_request_duration_seconds_bucket HTTP request duration buckets")
    lines.append("# TYPE http_request_duration_seconds_bucket histogram")
    lines.append(f"http_request_duration_seconds_bucket{{le=\"0.1\"}} {_count_bucket(endpoint_stats, 0.1)}")
    lines.append(f"http_request_duration_seconds_bucket{{le=\"0.5\"}} {_count_bucket(endpoint_stats, 0.5)}")
    lines.append(f"http_request_duration_seconds_bucket{{le=\"1.0\"}} {_count_bucket(endpoint_stats, 1.0)}")
    lines.append(f"http_request_duration_seconds_bucket{{le=\"5.0\"}} {_count_bucket(endpoint_stats, 5.0)}")
    lines.append(f"http_request_duration_seconds_bucket{{le=\"+Inf\"}} {summary_stats['total_requests']}")
    
    # Status code metrics
    for status_code, count in status_codes.items():
        lines.append(f"http_requests_total{{status=\"{status_code}\"}} {count}")
    
    # System metrics (if psutil available)
    if "error" not in system_metrics:
        memory = system_metrics.get("memory", {})
        cpu = system_metrics.get("cpu", {})
        
        lines.append("# HELP process_memory_bytes Process memory usage in bytes")
        lines.append("# TYPE process_memory_bytes gauge")
        lines.append(f"process_memory_bytes{{type=\"rss\"}} {memory.get('rss', 0)}")
        lines.append(f"process_memory_bytes{{type=\"vms\"}} {memory.get('vms', 0)}")
        
        lines.append("# HELP process_cpu_percent Process CPU usage percentage")
        lines.append("# TYPE process_cpu_percent gauge")
        lines.append(f"process_cpu_percent {cpu.get('percent', 0)}")
    
    # Uptime
    lines.append("# HELP http_server_uptime_seconds Server uptime in seconds")
    lines.append("# TYPE http_server_uptime_seconds counter")
    lines.append(f"http_server_uptime_seconds {summary_stats['uptime_seconds']}")
    
    return "\n".join(lines)


def _count_bucket(endpoint_stats: Dict[str, Dict[str, Any]], max_time: float) -> int:
    """Count requests in a time bucket."""
    count = 0
    for stats in endpoint_stats.values():
        if stats.get('avg_response_time_ms', 0) <= max_time * 1000:
            count += stats.get('requests', 0)
    return count


def generate_json_metrics() -> Dict[str, Any]:
    """Generate comprehensive JSON metrics."""
    metrics_collector = get_metrics_collector()
    
    return {
        "server": {
            "uptime_seconds": metrics_collector.get_summary_stats()["uptime_seconds"],
            "version": "1.0.0",
            "status": "running"
        },
        "requests": metrics_collector.get_summary_stats(),
        "endpoints": metrics_collector.get_endpoint_stats(),
        "clients": metrics_collector.get_ip_stats(),
        "status_codes": metrics_collector.get_status_code_stats(),
        "system": metrics_collector.get_system_metrics(),
        "recent_requests": metrics_collector.get_recent_requests(50)
    }


def handle_metrics_request(path: str, headers: dict) -> tuple[int, dict, bytes]:
    """Handle /metrics endpoint requests."""
    # Check for format preference
    accept_header = headers.get("accept", "").lower()
    
    if "application/json" in accept_header or path.endswith(".json"):
        # Return JSON format
        metrics_data = generate_json_metrics()
        body = json.dumps(metrics_data, indent=2).encode("utf-8")
        response_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    else:
        # Return Prometheus format (default)
        body = generate_prometheus_metrics().encode("utf-8")
        response_headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    
    return 200, response_headers, body
