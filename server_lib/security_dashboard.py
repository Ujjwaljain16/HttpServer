"""Security dashboard for monitoring attack attempts and security events."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from server_lib.rate_limiter import get_rate_limiter
from server_lib.request_limiter import get_request_limiter
from server_lib.security import log_security_violation


@dataclass
class SecurityEvent:
    """A security event/attack attempt."""
    timestamp: datetime
    event_type: str  # 'rate_limit', 'path_traversal', 'host_mismatch', 'request_too_large', etc.
    client_ip: str
    details: Dict[str, str]
    severity: str  # 'low', 'medium', 'high', 'critical'
    blocked: bool


class SecurityDashboard:
    """Thread-safe security dashboard for monitoring attacks."""
    
    def __init__(self, max_events: int = 10000):
        self._lock = threading.Lock()
        self._max_events = max_events
        
        # Event storage
        self._events: deque = deque(maxlen=max_events)
        self._events_by_ip: Dict[str, List[SecurityEvent]] = defaultdict(list)
        self._events_by_type: Dict[str, List[SecurityEvent]] = defaultdict(list)
        
        # Statistics
        self._total_events = 0
        self._blocked_requests = 0
        self._attack_attempts = 0
        
        # Real-time monitoring
        self._recent_attacks: deque = deque(maxlen=100)  # Last 100 attacks
        self._top_attackers: Dict[str, int] = defaultdict(int)
        self._attack_types: Dict[str, int] = defaultdict(int)
    
    def record_event(self, event: SecurityEvent) -> None:
        """Record a security event."""
        with self._lock:
            self._events.append(event)
            self._events_by_ip[event.client_ip].append(event)
            self._events_by_type[event.event_type].append(event)
            
            self._total_events += 1
            if event.blocked:
                self._blocked_requests += 1
            
            if event.severity in ['high', 'critical']:
                self._attack_attempts += 1
                self._recent_attacks.append(event)
                self._top_attackers[event.client_ip] += 1
                self._attack_types[event.event_type] += 1
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data."""
        with self._lock:
            current_time = datetime.now()
            
            # Time-based statistics
            last_hour = current_time - timedelta(hours=1)
            last_24h = current_time - timedelta(days=1)
            
            recent_events = [e for e in self._events if e.timestamp > last_hour]
            daily_events = [e for e in self._events if e.timestamp > last_24h]
            
            # Top attackers (last 24h)
            attacker_counts = defaultdict(int)
            for event in daily_events:
                if event.severity in ['high', 'critical']:
                    attacker_counts[event.client_ip] += 1
            
            top_attackers = sorted(attacker_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Attack type distribution
            type_counts = defaultdict(int)
            for event in daily_events:
                type_counts[event.event_type] += 1
            
            # Severity distribution
            severity_counts = defaultdict(int)
            for event in daily_events:
                severity_counts[event.severity] += 1
            
            return {
                "summary": {
                    "total_events": self._total_events,
                    "blocked_requests": self._blocked_requests,
                    "attack_attempts": self._attack_attempts,
                    "events_last_hour": len(recent_events),
                    "events_last_24h": len(daily_events)
                },
                "recent_attacks": [
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "type": event.event_type,
                        "client_ip": event.client_ip,
                        "severity": event.severity,
                        "blocked": event.blocked,
                        "details": event.details
                    }
                    for event in list(self._recent_attacks)[-20:]  # Last 20 attacks
                ],
                "top_attackers": [
                    {"ip": ip, "attack_count": count}
                    for ip, count in top_attackers
                ],
                "attack_types": dict(type_counts),
                "severity_distribution": dict(severity_counts),
                "rate_limiter_stats": get_rate_limiter().get_stats(),
                "request_limiter_stats": get_request_limiter().get_stats()
            }
    
    def get_events_by_ip(self, client_ip: str, limit: int = 100) -> List[Dict]:
        """Get events for a specific IP address."""
        with self._lock:
            events = self._events_by_ip.get(client_ip, [])
            return [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "type": event.event_type,
                    "severity": event.severity,
                    "blocked": event.blocked,
                    "details": event.details
                }
                for event in events[-limit:]
            ]
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict]:
        """Get events of a specific type."""
        with self._lock:
            events = self._events_by_type.get(event_type, [])
            return [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "client_ip": event.client_ip,
                    "severity": event.severity,
                    "blocked": event.blocked,
                    "details": event.details
                }
                for event in events[-limit:]
            ]
    
    def is_ip_blocked(self, client_ip: str) -> bool:
        """Check if an IP is currently blocked."""
        with self._lock:
            # Check recent high-severity events
            recent_events = [e for e in self._events 
                           if e.client_ip == client_ip and 
                           e.timestamp > datetime.now() - timedelta(minutes=5) and
                           e.severity in ['high', 'critical']]
            return len(recent_events) >= 5  # Block if 5+ high-severity events in 5 minutes
    
    def get_security_report(self) -> str:
        """Generate a text security report."""
        data = self.get_dashboard_data()
        
        report = f"""
SECURITY DASHBOARD REPORT
========================
Generated: {datetime.now().isoformat()}

SUMMARY:
- Total Security Events: {data['summary']['total_events']}
- Blocked Requests: {data['summary']['blocked_requests']}
- Attack Attempts: {data['summary']['attack_attempts']}
- Events (Last Hour): {data['summary']['events_last_hour']}
- Events (Last 24h): {data['summary']['events_last_24h']}

TOP ATTACKERS (Last 24h):
"""
        for attacker in data['top_attackers'][:5]:
            report += f"- {attacker['ip']}: {attacker['attack_count']} attacks\n"
        
        report += f"\nATTACK TYPES (Last 24h):\n"
        for attack_type, count in data['attack_types'].items():
            report += f"- {attack_type}: {count}\n"
        
        report += f"\nSEVERITY DISTRIBUTION (Last 24h):\n"
        for severity, count in data['severity_distribution'].items():
            report += f"- {severity}: {count}\n"
        
        return report


# Global security dashboard instance
_security_dashboard: Optional[SecurityDashboard] = None


def get_security_dashboard() -> SecurityDashboard:
    """Get the global security dashboard instance."""
    global _security_dashboard
    if _security_dashboard is None:
        _security_dashboard = SecurityDashboard()
    return _security_dashboard


def record_security_event(event_type: str, client_ip: str, details: Dict[str, str], 
                         severity: str = "medium", blocked: bool = False) -> None:
    """Convenience function to record a security event."""
    event = SecurityEvent(
        timestamp=datetime.now(),
        event_type=event_type,
        client_ip=client_ip,
        details=details,
        severity=severity,
        blocked=blocked
    )
    get_security_dashboard().record_event(event)


def handle_security_dashboard_request(path: str, headers: dict) -> tuple[int, dict, bytes]:
    """Handle /security-dashboard endpoint requests."""
    dashboard = get_security_dashboard()
    
    # Check for format preference
    accept_header = headers.get("accept", "").lower()
    
    if "application/json" in accept_header or path.endswith(".json"):
        # Return JSON format
        dashboard_data = dashboard.get_dashboard_data()
        body = json.dumps(dashboard_data, indent=2).encode("utf-8")
        response_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    else:
        # Return HTML dashboard
        dashboard_data = dashboard.get_dashboard_data()
        html = generate_security_dashboard_html(dashboard_data)
        body = html.encode("utf-8")
        response_headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    
    return 200, response_headers, body


def generate_security_dashboard_html(data: Dict) -> str:
    """Generate HTML security dashboard."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #e0e0e0; padding-bottom: 20px; margin-bottom: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .section {{ margin-bottom: 30px; }}
        .section h3 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .severity-high {{ color: #dc3545; font-weight: bold; }}
        .severity-critical {{ color: #721c24; font-weight: bold; background: #f8d7da; }}
        .severity-medium {{ color: #856404; font-weight: bold; }}
        .severity-low {{ color: #155724; }}
        .refresh-btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #0056b3; }}
    </style>
    <script>
        function refreshDashboard() {{
            location.reload();
        }}
        // Auto-refresh every 30 seconds
        setInterval(refreshDashboard, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Security Dashboard</h1>
            <p>Real-time security monitoring and attack detection</p>
            <button class="refresh-btn" onclick="refreshDashboard()">Refresh</button>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{data['summary']['total_events']}</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{data['summary']['blocked_requests']}</div>
                <div class="stat-label">Blocked Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{data['summary']['attack_attempts']}</div>
                <div class="stat-label">Attack Attempts</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{data['summary']['events_last_hour']}</div>
                <div class="stat-label">Events (Last Hour)</div>
            </div>
        </div>
        
        <div class="section">
            <h3>🚨 Recent Attacks</h3>
            <table>
                <tr><th>Time</th><th>Type</th><th>IP</th><th>Severity</th><th>Blocked</th><th>Details</th></tr>
                {''.join(f'<tr><td>{attack["timestamp"]}</td><td>{attack["type"]}</td><td>{attack["client_ip"]}</td><td class="severity-{attack["severity"]}">{attack["severity"]}</td><td>{"Yes" if attack["blocked"] else "No"}</td><td>{attack["details"]}</td></tr>' for attack in data['recent_attacks'])}
            </table>
        </div>
        
        <div class="section">
            <h3>🎯 Top Attackers (Last 24h)</h3>
            <table>
                <tr><th>IP Address</th><th>Attack Count</th></tr>
                {''.join(f'<tr><td>{attacker["ip"]}</td><td>{attacker["attack_count"]}</td></tr>' for attacker in data['top_attackers'])}
            </table>
        </div>
        
        <div class="section">
            <h3>📊 Attack Types (Last 24h)</h3>
            <table>
                <tr><th>Attack Type</th><th>Count</th></tr>
                {''.join(f'<tr><td>{attack_type}</td><td>{count}</td></tr>' for attack_type, count in data['attack_types'].items())}
            </table>
        </div>
        
        <div class="section">
            <h3>⚠️ Severity Distribution (Last 24h)</h3>
            <table>
                <tr><th>Severity</th><th>Count</th></tr>
                {''.join(f'<tr><td class="severity-{severity}">{severity}</td><td>{count}</td></tr>' for severity, count in data['severity_distribution'].items())}
            </table>
        </div>
    </div>
</body>
</html>
"""
