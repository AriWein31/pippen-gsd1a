"""Night alarm system for safety-critical coverage monitoring."""

from .engine import (
    AlarmStatus,
    NotificationChannel,
    CoverageAlarmEngine,
    Clock,
    SystemClock,
    NotificationService,
    NotificationMessage,
)
from .daemon import AlarmDaemon
from .watchdog import AlarmDaemonWatchdog, DaemonHealth

__all__ = [
    "AlarmStatus",
    "NotificationChannel",
    "CoverageAlarmEngine",
    "Clock",
    "SystemClock",
    "NotificationService",
    "NotificationMessage",
    "AlarmDaemon",
    "AlarmDaemonWatchdog",
    "DaemonHealth",
]
