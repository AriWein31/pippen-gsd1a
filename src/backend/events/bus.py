"""
Event Bus — Pub/sub system for reacting to events.

The coverage engine and other components subscribe to events
instead of polling the database.

This is a minimal interface for Week 2. Production will use
a proper message queue (Redis Pub/Sub, RabbitMQ, or NATS).
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Any
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventBus(ABC):
    """Abstract interface for event publishing/subscription."""
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to events of a specific type."""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Unsubscribe a handler from events."""
        pass


class InMemoryEventBus(EventBus):
    """
    In-memory event bus for development and testing.
    
    NOTE: This is NOT suitable for production with multiple processes.
    Production will use Redis Pub/Sub or similar.
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = asyncio.Lock()
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publish event to all subscribers."""
        event = {
            "type": event_type,
            "data": event_data,
            "published_at": datetime.utcnow().isoformat(),
        }
        
        async with self._lock:
            handlers = self._subscribers.get(event_type, []).copy()
        
        # Call handlers outside the lock
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler failed for {event_type}: {e}")
    
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Handler subscribed to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Unsubscribe a handler from events."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            logger.info(f"Handler unsubscribed from {event_type}")


# Global event bus instance (will be replaced with Redis in production)
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = InMemoryEventBus()
    return _event_bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus (for testing)."""
    global _event_bus
    _event_bus = bus


# Event types for Week 2 coverage engine
class EventTypes:
    """Event type constants."""
    
    # Patient events
    GLUCOSE_LOGGED = "glucose.logged"
    CORNSTARCH_LOGGED = "cornstarch.logged"
    MEAL_LOGGED = "meal.logged"
    SYMPTOM_LOGGED = "symptom.logged"
    
    # Coverage events
    COVERAGE_COURSE_STARTED = "coverage.course_started"
    COVERAGE_COURSE_WARNING = "coverage.course_warning"
    COVERAGE_COURSE_EXPIRED = "coverage.course_expired"
    COVERAGE_COURSE_CLOSED = "coverage.course_closed"
    
    # Alarm events
    ALARM_TRIGGERED = "alarm.triggered"
    ALARM_ACKNOWLEDGED = "alarm.acknowledged"
    ALARM_ESCALATED = "alarm.escalated"
    
    # System events
    EVENT_STORED = "event.stored"
    EVENT_AMENDED = "event.amended"
