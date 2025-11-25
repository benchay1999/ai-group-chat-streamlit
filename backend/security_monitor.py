"""
Real-Time Security Monitoring and Alerting System

Monitors security-critical events and sends alerts when suspicious activity is detected.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json


class SecurityEventType(str, Enum):
    """Types of security events to monitor."""
    FAILED_LOGIN = "failed_login"
    DUPLICATE_PAYMENT = "duplicate_payment"
    CONCURRENT_SESSION_CONFLICT = "concurrent_session_conflict"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    DATABASE_ERROR = "database_error"
    UNUSUAL_CASHOUT = "unusual_cashout"
    INVALID_TOKEN = "invalid_token"
    ADMIN_ACCESS_ATTEMPT = "admin_access_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"


class SeverityLevel(str, Enum):
    """Severity levels for security events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_type: SecurityEventType
    severity: SeverityLevel
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "details": self.details
        }


class SecurityMonitor:
    """Real-time security event monitoring system."""
    
    def __init__(self):
        """Initialize security monitor."""
        self.events: List[SecurityEvent] = []
        self.event_counts: Dict[SecurityEventType, int] = defaultdict(int)
        self.ip_failed_logins: Dict[str, List[datetime]] = defaultdict(list)
        self.user_failed_logins: Dict[str, List[datetime]] = defaultdict(list)
        self.alerts_sent: List[Dict] = []
        
        # Thresholds for alerting
        self.FAILED_LOGIN_THRESHOLD = 5  # 5 failed logins in window
        self.FAILED_LOGIN_WINDOW = 300  # 5 minutes
        self.UNUSUAL_CASHOUT_AMOUNT = 50.00  # $50+ cashout is unusual
        self.MAX_EVENTS_IN_MEMORY = 10000  # Prevent memory leak
    
    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SeverityLevel,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            user_id: User ID if applicable
            ip_address: IP address if applicable
            details: Additional event details
        """
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            details=details or {}
        )
        
        self.events.append(event)
        self.event_counts[event_type] += 1
        
        # Enforce memory limit
        if len(self.events) > self.MAX_EVENTS_IN_MEMORY:
            # Remove oldest 20%
            remove_count = int(self.MAX_EVENTS_IN_MEMORY * 0.2)
            self.events = self.events[remove_count:]
        
        # Check if alert should be triggered
        self._check_alert_conditions(event)
        
        # Log to console
        self._log_to_console(event)
    
    def _check_alert_conditions(self, event: SecurityEvent):
        """Check if event should trigger an alert."""
        # Failed login tracking
        if event.event_type == SecurityEventType.FAILED_LOGIN:
            if event.ip_address:
                self.ip_failed_logins[event.ip_address].append(event.timestamp)
                
                # Clean old entries
                cutoff = datetime.utcnow() - timedelta(seconds=self.FAILED_LOGIN_WINDOW)
                self.ip_failed_logins[event.ip_address] = [
                    ts for ts in self.ip_failed_logins[event.ip_address]
                    if ts > cutoff
                ]
                
                # Check threshold
                if len(self.ip_failed_logins[event.ip_address]) >= self.FAILED_LOGIN_THRESHOLD:
                    self._send_alert(
                        f"🚨 BRUTE FORCE ATTACK DETECTED",
                        f"IP {event.ip_address} had {len(self.ip_failed_logins[event.ip_address])} "
                        f"failed logins in {self.FAILED_LOGIN_WINDOW}s",
                        SeverityLevel.HIGH
                    )
        
        # Critical events always alert
        if event.severity == SeverityLevel.CRITICAL:
            self._send_alert(
                f"🚨 CRITICAL SECURITY EVENT",
                f"{event.event_type.value}: {event.details}",
                SeverityLevel.CRITICAL
            )
        
        # Unusual cashout amounts
        if event.event_type == SecurityEventType.UNUSUAL_CASHOUT:
            amount = event.details.get('amount_usd', 0)
            if amount >= self.UNUSUAL_CASHOUT_AMOUNT:
                self._send_alert(
                    f"⚠️  UNUSUAL CASHOUT DETECTED",
                    f"User {event.user_id} requested ${amount} cashout",
                    SeverityLevel.MEDIUM
                )
    
    def _send_alert(self, title: str, message: str, severity: SeverityLevel):
        """
        Send security alert.
        
        In production, this should:
        - Send email to admins
        - Post to Slack/Discord
        - Trigger PagerDuty for critical events
        
        For now, logs to console and stores in memory.
        """
        alert = {
            "title": title,
            "message": message,
            "severity": severity.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.alerts_sent.append(alert)
        
        # Print alert
        print(f"\n{'!' * 70}")
        print(f"{title}")
        print(f"{message}")
        print(f"Severity: {severity.value.upper()}")
        print(f"Time: {alert['timestamp']}")
        print(f"{'!' * 70}\n")
        
        # TODO: Integrate with:
        # - Email: smtplib or SendGrid
        # - Slack: slack_sdk
        # - Discord: discord webhooks
        # - PagerDuty: pypd
    
    def _log_to_console(self, event: SecurityEvent):
        """Log event to console with color coding."""
        severity_icons = {
            SeverityLevel.LOW: "ℹ️",
            SeverityLevel.MEDIUM: "⚠️",
            SeverityLevel.HIGH: "🚨",
            SeverityLevel.CRITICAL: "🔥"
        }
        
        icon = severity_icons.get(event.severity, "📝")
        
        print(
            f"{icon} [{event.timestamp.strftime('%H:%M:%S')}] "
            f"{event.event_type.value.upper()} - "
            f"User: {event.user_id or 'N/A'}, "
            f"IP: {event.ip_address or 'N/A'}"
        )
        
        if event.details:
            print(f"   Details: {json.dumps(event.details, indent=2)}")
    
    def get_recent_events(self, minutes: int = 60) -> List[SecurityEvent]:
        """Get security events from last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp > cutoff]
    
    def get_event_summary(self) -> Dict:
        """Get summary of security events."""
        recent_events = self.get_recent_events(60)
        
        return {
            "total_events": len(self.events),
            "recent_events_1h": len(recent_events),
            "event_counts": {k.value: v for k, v in self.event_counts.items()},
            "alerts_sent": len(self.alerts_sent),
            "recent_alerts": self.alerts_sent[-10:] if self.alerts_sent else []
        }


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """Get or create global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor


# Convenience functions for logging specific events

def log_failed_login(user_id: str, ip_address: str, reason: str = "Invalid credentials"):
    """Log a failed login attempt."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.FAILED_LOGIN,
        severity=SeverityLevel.MEDIUM,
        user_id=user_id,
        ip_address=ip_address,
        details={"reason": reason}
    )


def log_duplicate_payment_attempt(user_id: str, details: Dict):
    """Log a duplicate payment attempt."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.DUPLICATE_PAYMENT,
        severity=SeverityLevel.HIGH,
        user_id=user_id,
        details=details
    )


def log_rate_limit_violation(ip_address: str, endpoint: str):
    """Log a rate limit violation."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.RATE_LIMIT_VIOLATION,
        severity=SeverityLevel.LOW,
        ip_address=ip_address,
        details={"endpoint": endpoint}
    )


def log_invalid_token(user_id: Optional[str], ip_address: str, reason: str):
    """Log an invalid token usage attempt."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.INVALID_TOKEN,
        severity=SeverityLevel.MEDIUM,
        user_id=user_id,
        ip_address=ip_address,
        details={"reason": reason}
    )


def log_admin_access_attempt(user_id: str, endpoint: str, allowed: bool):
    """Log an admin endpoint access attempt."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.ADMIN_ACCESS_ATTEMPT,
        severity=SeverityLevel.HIGH if not allowed else SeverityLevel.LOW,
        user_id=user_id,
        details={"endpoint": endpoint, "allowed": allowed}
    )


def log_unusual_cashout(user_id: str, amount_usd: float):
    """Log an unusual cashout request."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.UNUSUAL_CASHOUT,
        severity=SeverityLevel.MEDIUM,
        user_id=user_id,
        details={"amount_usd": amount_usd}
    )


def log_sql_injection_attempt(ip_address: str, payload: str):
    """Log a potential SQL injection attempt."""
    monitor = get_security_monitor()
    monitor.log_event(
        event_type=SecurityEventType.SQL_INJECTION_ATTEMPT,
        severity=SeverityLevel.CRITICAL,
        ip_address=ip_address,
        details={"payload": payload[:100]}  # Truncate for safety
    )

